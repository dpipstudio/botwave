from datetime import datetime

from shared.env import Env
from shared.logger import Log
from shared.protocol import Commands, ProtocolParser, PROTOCOL_VERSION
from shared.protomanager import ProtoManager
from shared.ops import GeneralOp
from shared.version import versions_compatible

class BotWaveClient:
    def __init__(self, client_id: str, websocket, machine_info: dict, protocol_version: str):
        self.client_id = client_id
        self.websocket = websocket
        self.proto = ProtoManager(send_fn=websocket.send)
        self.machine_info = machine_info
        self.protocol_version = protocol_version
        self.connected_at = datetime.now()
        self.last_seen = datetime.now()

    def get_display_name(self) -> str:
        hostname = self.machine_info.get('hostname', 'unknown')
        return f"{hostname} ({self.client_id})"

class RegisterOp(GeneralOp):
    commands = {
        Commands.REGISTER: "register",
        Commands.AUTH: "auth",
        Commands.VER: "ver"
    }

    async def register(self, client_id, parsed, websocket):
        self.setup_attr(websocket)

        kwargs = parsed['kwargs']

        machine_info = {
            'hostname': kwargs.get('hostname', 'unknown'),
            'machine': kwargs.get('machine', 'unknown'),
            'system': kwargs.get('system', 'unknown'),
            'release': kwargs.get('release', 'unknown')
        }
        
        websocket.reg_data['machine_info'] = machine_info
        
        Log.info(f"Registration attempt from {machine_info['hostname']}")
        
        if not Env.get("PASSKEY"):
            websocket.reg_data['authenticated'] = True

    async def auth(self, client_id, parsed, websocket):
        self.setup_attr(websocket)

        args = parsed['args']
        passkey = Env.get("PASSKEY")

        if not passkey:
            websocket.reg_data['authenticated'] = True
            return
        
        if not args:
            Log.auth("AUTH command missing passkey")
            error = ProtocolParser.build_response(
                Commands.AUTH_FAILED,
                "Missing passkey"
            )
            await websocket.send(error)
            await websocket.close()
            return
        
        client_passkey = args[0]
        
        if client_passkey != passkey:
            Log.auth(f"Authentication failed: Invalid passkey")
            error = ProtocolParser.build_response(
                Commands.AUTH_FAILED,
                "Invalid passkey"
            )
            await websocket.send(error)
            await websocket.close()
            return
        
        websocket.reg_data['authenticated'] = True
        Log.auth("Client authenticated")

    async def ver(self, client_id, parsed, websocket):
        self.setup_attr(websocket)

        args = parsed['args']

        if not args:
            Log.error("VER command missing version")
            error = ProtocolParser.build_response(
                Commands.ERROR,
                message="Missing protocol version"
            )
            await websocket.send(error)
            await websocket.close()
            return
        
        client_version = args[0]
        
        if not versions_compatible(PROTOCOL_VERSION, client_version) and not Env.get_bool("ALLOW_PROTO_MISMATCH"):
            Log.error(f"Protocol version mismatch!")
            Log.error(f"  Server version: {PROTOCOL_VERSION}")
            Log.error(f"  Client version: {client_version}")
            
            error = ProtocolParser.build_command(
                Commands.VERSION_MISMATCH,
                server_version=PROTOCOL_VERSION,
                client_version=client_version,
                message=f"Protocol version mismatch. Please update."
            )
            await websocket.send(error)
            await websocket.close()
            return
        
        websocket.reg_data['protocol_version'] = client_version
        
        if (websocket.reg_data['machine_info'] and 
            websocket.reg_data['authenticated'] and 
            websocket.reg_data['protocol_version']):
            
            await self.complete_reg(websocket)

        else:
            if not websocket.reg_data['authenticated']:
                Log.auth("Client did not authenticate. Perhaps a missing passkey?")

                error = ProtocolParser.build_response(
                    Commands.AUTH_FAILED,
                    message="Authentication required"
                )
                await websocket.send(error)
                await websocket.close()
        
        return

    async def complete_reg(self, websocket):
            
            reg_data = websocket.reg_data
            machine_info = reg_data['machine_info']
            protocol_version = reg_data['protocol_version']
            hostname = machine_info['hostname']
            ip = "unknown"
    
            try:
                ip = websocket.remote_address[0]
            except:
                pass
            
            base_client_id = f"{hostname}_{ip}"
            client_id = base_client_id
            
            if client_id in self.owner.clients:
                Log.warning(f"Client {client_id} reconnected")
                old_client = self.owner.clients[client_id]

                try:
                    await old_client.websocket.close()

                except:
                    pass

                del self.owner.clients[client_id]
                
                client_id = base_client_id
            
            client = BotWaveClient(
                client_id=client_id,
                websocket=websocket,
                machine_info=machine_info,
                protocol_version=protocol_version
            )
            
            self.owner.clients[client_id] = client
            
            self.owner.ws_server.register_client(websocket, client_id)
            
            response = ProtocolParser.build_command(
                Commands.REGISTER_OK,
                client_id=client_id,
                server_version=PROTOCOL_VERSION
            )
            
            await websocket.send(response)
            
            Log.success(f"Client registered: {client.get_display_name()}")
    
            if protocol_version != PROTOCOL_VERSION:
                Log.version(f"Client protocol version ({protocol_version}) does not match ours ({PROTOCOL_VERSION}). Some features may not work correctly.")
            
            delattr(websocket, 'reg_data')
            await self.registry.dispatch("handlers_onconnect", client_id=client_id)

    def setup_attr(self, websocket):
        if not hasattr(websocket, 'reg_data'):
            websocket.reg_data = {
                'machine_info': None,
                'authenticated': False,
                'protocol_version': None
            }

def setup(reg):
    reg.register(RegisterOp)