import asyncio
from typing import Callable, Awaitable

from shared.logger import Log
from shared.protocol import ProtocolParser, Commands, gen_tx


class CommandHandle:
    """
    Handle returned by ProtoManager.execute().
    Can be awaited directly, or used to cancel / manually complete the command.
    """

    def __init__(self, tx_id: str, future: asyncio.Future, context: dict, cancel_cb: Callable):
        self.tx_id = tx_id
        self.__future = future
        self.__ctx = context
        self.__cancel = cancel_cb

    def cancel(self):
        """Cancel the command, triggering on_error with a TimeoutError."""
        
        self.__cancel(self.tx_id, TimeoutError("Cancelled"))

    def complete(self):
        """
        Manually resolve the handle with the last received response.
        Useful when using expect_multiple=True and you decide the command is done.
        """

        if not self.__future.done():
            self.__future.set_result(self.__ctx.get('last_response'))

    def __await__(self):
        return self.__future.__await__()


class ProtoManager:
    """
    Promise-based command execution layer on top of a websocket send callable.

    Wraps any async send function and provides execute(), send(), fire() and dispatch()
    to handle request/response tracking via transaction IDs.

    Usage:
        proto = ProtoManager(send_fn=ws.send)

        # fire and forget
        await proto.fire(Commands.PING)

        # await directly
        response = await proto.send(Commands.LIST_FILES)

        # callback style
        proto.execute(Commands.START, filename="song.wav",
                      on_ok=lambda d: print("started"),
                      on_error=lambda e: print(f"failed: {e}"),
                      timeout=5.0)

    Every incoming message must be passed to dispatch() so pending futures can be resolved.
    """

    def __init__(self, send_fn: Callable[[str], Awaitable] = None, default_timeout: float = 10.0):
        self.__send_func = send_fn
        self.__pending: dict[str, tuple] = {}
        self.__timeout = default_timeout

    def __safe_call(self, fn: Callable, *args):
        """Call a callback safely, logging any exceptions instead of crashing."""
        if fn is None:
            return
        try:
            fn(*args)
        except Exception as e:
            Log.error(f"Callback error: {e}")

    def execute(self, command: str, *args,
                on_ok: Callable = None,
                on_error: Callable = None,
                expect_multiple: bool = False,
                timeout: float = None,
                **kwargs) -> CommandHandle:
        """
        Send a command and return a CommandHandle.

        Non-blocking — returns immediately. The handle can be awaited,
        or you can rely purely on on_ok / on_error callbacks.

        Args:
            command:         Command name (e.g. Commands.START)
            *args:           Positional arguments passed to the command
            on_ok:           Called with the response dict when OK (or any non-ERROR response)
            on_error:        Called with the exception on ERROR or timeout
            expect_multiple: If True, the handle won't auto-complete on the first OK.
                             Call handle.complete() or handle.cancel() manually.
            timeout:         Per-request timeout in seconds. Defaults to the instance default.
            **kwargs:        Keyword arguments passed to the command

        Returns:
            CommandHandle
        """

        loop = asyncio.get_event_loop()
        tx_id = gen_tx()
        future = loop.create_future()
        future.add_done_callback(lambda f: f.exception() if f.done() and not f.cancelled() else None) # to avoid printing exceptions

        context = {
            'command': command,
            'callbacks': {
                'on_ok': on_ok,
                'on_error': on_error,
            },
            'expect_multiple': expect_multiple,
            'last_response': None,
            'timer': None,
        }

        def cancel(tx_id, exc=None):
            self.__pending.pop(tx_id, None)
            if not future.done():
                err = exc or asyncio.CancelledError()
                future.set_exception(err)
                self.__safe_call(on_error, err)
            if context['timer']:
                context['timer'].cancel()

        t = timeout or self.__timeout
        if t:
            context['timer'] = loop.call_later(
                t, cancel, tx_id,
                TimeoutError(f"{command} timed out after {t}s")
            )

        self.__pending[tx_id] = (future, context, cancel)

        msg = ProtocolParser.build_command(command, *args, transaction_id=tx_id, **kwargs)
        asyncio.ensure_future(self.__send_func(msg))

        return CommandHandle(tx_id, future, context, cancel)

    async def send(self, command: str, *args,
                   expected: tuple = (Commands.OK,),
                   timeout: float = None,
                   **kwargs) -> dict:
        """
        Send a command and await the response directly.

        Raises RuntimeError on ERROR response or unexpected response type.
        Raises TimeoutError if no response is received within the timeout.

        Args:
            command:  Command name
            *args:    Positional arguments
            expected: Tuple of accepted response commands. Defaults to (OK,).
            timeout:  Per-request timeout in seconds. Defaults to the instance default.
            **kwargs: Keyword arguments passed to the command

        Returns:
            Parsed response dict

        Example:
            response = await proto.send(Commands.REGISTER, hostname="pi1",
                                        expected=(Commands.REGISTER_OK,))
        """

        future = asyncio.get_event_loop().create_future()

        def on_ok(data):
            if not future.done():
                if data['command'] not in expected:
                    future.set_exception(RuntimeError(f"Unexpected response: {data['command']}"))
                else:
                    future.set_result(data)

        def on_error(err):
            if not future.done():
                future.set_exception(err)

        self.execute(command, *args, on_ok=on_ok, on_error=on_error, timeout=timeout, **kwargs)

        return await future

    async def fire(self, command: str, *args, **kwargs):
        """
        Send a command with no response tracking.

        No transaction_id is attached. Use for commands where you don't
        care about the response (e.g. PING, PONG, KICK).

        Args:
            command:  Command name
            *args:    Positional arguments
            **kwargs: Keyword arguments
        """

        msg = ProtocolParser.build_command(command, *args, **kwargs)
        await self.__send_func(msg)

    def dispatch(self, parsed: dict) -> bool:
        """
        Route an incoming parsed message to its pending future/callbacks.

        Call this at the top of every message handler. Returns True if the
        message was consumed (matched a pending transaction), False if it
        should be handled normally (broadcasts, pings, etc).

        Args:
            parsed: Output of ProtocolParser.parse_command()

        Returns:
            True if the message matched a pending transaction, False otherwise.

        Example:
            async def _handle_message(self, message: str):
                parsed = ProtocolParser.parse_command(message)
                if self.proto.dispatch(parsed):
                    return
                # handle broadcasts / non-tracked commands below
        """

        tx_id = parsed.get('kwargs', {}).get('transaction_id')
        if not tx_id or tx_id not in self.__pending:
            return False

        future, context, cancel = self.__pending[tx_id]
        if future.done():
            return True

        callbacks = context['callbacks']
        command = parsed['command']
        context['last_response'] = parsed

        if command == Commands.ERROR:
            err = RuntimeError(parsed['kwargs'].get('message', 'Unknown error'))
            err.data = parsed
            self.__safe_call(callbacks['on_error'], err)
            cancel(tx_id)
            return True

        if command == Commands.OK:
            self.__safe_call(callbacks['on_ok'], parsed)
            if not context['expect_multiple']:
                cancel(tx_id)
            return True

        # any other non-error response (custom response types, etc)
        self.__safe_call(callbacks['on_ok'], parsed)
        return True
    
    async def reply(self, parsed: dict, command: str, **kwargs):
        tx_id = parsed['kwargs'].get('transaction_id')

        if tx_id:
            kwargs['transaction_id'] = tx_id

        await self.fire(command, **kwargs)