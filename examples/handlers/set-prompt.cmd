#!/*/set-prompt
#> syntax "[new_prompt] [permanent]"
#> short_help "Update the BotWave prompt"

#? This command updates the BotWave Prompt.
#? If [new_prompt] is provided, update the prompt to it.
#? Else, set the prompt back to "botwave ›".
#?
#? If [permanant] is set to "true", the prompt will be stored
#? in the /opt/BotWave/.env file.
#?
#? Repository: https://github.com/dpipstudio/botwave

| bash /opt/BotWave/scripts/bw_examples/set-prompt.sh