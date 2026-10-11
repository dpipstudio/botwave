#!/*/update-botwave
#> syntax ""
#> short_help "Update BotWave and restart it"

#? Runs "bw-update" to update BotWave to the latest
#? released version. Once updated, restarts the
#? systemd service installed by bw-autorun to apply
#? the changes.
#?
#? This command can't be executed by remote clients
#? except if "ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING"
#? is set to "true".
#?
#? Repository: https://github.com/dpipstudio/botwave

# prevent remote execution
| bash /opt/BotWave/scripts/bw_examples/localonly.sh

| bash /opt/BotWave/scripts/bw_examples/update.sh