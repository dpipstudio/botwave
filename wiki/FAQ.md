# BotWave FAQ

Here you'll find the most asked questions ! If this page didn't reply to your needs, please don't be ashamed to ask questions in the issues !

## General questions

**Q: What is BotWave ?**  
**A:** BotWave is a server-client system that allows you to broadcast audio files over FM radio using Raspberry Pi devices. It enables you to manage multiple Raspberry Pis from a central server, upload audio files, and control broadcasts remotely. It also comes with a standalone client that doesn't need any server.  
  
**Q: Is BotWave legal to use ?**  
**A:** Broadcasting on FM frequencies may be subject to local regulations and laws. It's your responsibility to ensure compliance with applicable legal requirements in your area. Unauthorized broadcasting may result in fines or penalties. Always check your local regulations before broadcasting. Please note that due of the hardware of the raspberry pi, harmonics **ARE** generated on `3x`, `5x`, `7x` and `9x` the desired frequency. Those harmonics are polluting important services like emergency services a d others. We recommand at least using a band-pass filter if you plan on reaching important ranges.  
  
**Q: What Raspberry Pi models are supported ?**  
**A:** BotWave works on most Raspberry Pi models (Pi 2, 3, 4, Zero, etc.), except on the Raspberry Pi 5 and pico. However, performance may vary. The Pi needs GPIO access for FM transmission, so it must run as root.  
  
> [!CAUTION]
> You might want to read this
  
**Q: How can I try to keep the signal in my house, and not overlapping on important signals outside my house ?**  
**A:** To limit your broadcast range indoors, use a very short antenna (or just the GPIO pin without a wire) and place your Raspberry Pi away from windows and doors. Keeping the Pi in the center of your home reduces the risk of the signal leaking outside. Avoid long wires as an antenna (or putting your pi next to a metallic structure), as they increase range. This way, your broadcast will stay mostly inside your home while still being clear for nearby listening.
  

**Q: Do I need an antenna ?**  
**A:** Not necessarily. If you have gpio headers soldered on your board, they can act as a very tiny and limited antenna that is enough for >= 1 meters around the pi. If you need more range and stability, you'll have to connect an antenna or wire to GPIO 4 (pin 7) on your Raspberry Pi. The length and type of antenna will affect your broadcast range and quality. You might want to check the example images on [Base/Setup#wireing](https://github.com/dpipstudio/botwave/wiki/Setup#wireing).  
  
**Q: Should I use a band-pass filter ?**  
**A:** As mentionned earlier, it is strongly recommended if you plan on reaching wide ranges. A band-pass filter helps minimize interference and keeps your signal within the intended frequency range, preventing harmonics from affecting other frequencies.  
  
**Q: How do I install BotWave ?**  
**A:** We do have an automatic installer, however, we recommand reading the [Base/Setup](https://github.com/dpipstudio/botwave/wiki/Setup) article for installation details.  
  
**Q: Can I run the server on a Raspberry Pi ?**  
**A:** Yes! You can run the server on any Linux system, including a Raspberry Pi. However, dedicated server hardware (like a desktop or cloud server) may offer better performance when managing many clients.

**Q: How do I update my BotWave installation ?**  
**A:** Simply run `bw-update` on a shell !  
  
**Q: How do I uninstall my BotWave installation ?**  
**A:** You can uninstall BotWave by running `curl -sSL https://botwave.dpip.lol/uninstall | sudo bash` in your shell. Please note that `/opt/BotWave/` will be deleted, so be sure to backup important files !  
  
**Q: What frequency should I use ?**  
**A:** Choose an unused FM frequency in the range 76.0 -> 108.0 MHz. Use an FM radio to scan for empty frequencies in your area. Avoid using frequencies occupied by commercial stations.

**Q: What audio format should I use?**
**A:** BotWave works with WAV files at 44.1kHz, 16-bit, mono or stereo. Other formats may need conversion (use `ffmpeg` or an online tool to convert).  
  
**Q: What is RDS ?**  
**A:** RDS (Radio Data System) displays text information on FM radios. BotWave supports PS (station name), RT (radio text), and PI (program identification) settings.

**Q: What is SSTV ?**  
**A:** SSTV is a method of transmitting images over radio. BotWave can convert images to SSTV audio and broadcast them over FM. 

**Q: What SSTV modes are supported ?**  
**A:** BotWave supports all [PySSTV](https://github.com/dnet/pySSTV) modes (Robot36, Martin1, Martin2, Scottie1, Scottie2, etc.). If you don't specify a mode, it auto-selects the best one.  
  
**Q: What is local mode ?**  
**A:** Local Mode lets you broadcast directly from a Raspberry Pi without a server. It's useful for standalone setups or testing.

**Q: How can I contribute ?**  
**A:** Contributions are welcome! Check the [For Developers/Contributing to BotWave](https://none.com) section in the wiki for contribution guidelines.

## Troubleshooting
This part of the FAQ will focus on troubleshooting common errors. (**I**ssue/**S**olution)

**I: My client won't connect to the server**  
**S:** Start by checking if the IP address is correct. Then ensure that ports 9938 and 9921 are open. This can be done by using the `telnet <ip> <port>` command. If it tells you that the connection has been established, it should be fine. Then verify if both the client and the server are using the same protocol version. Finally, if using a passkey, make sure it matches on both sides.  
  
**I: I'm getting "Protocol version mismatch"**  
**S:** Update both server and client to the latest version: `bw-update`.  
  
**I: The broadcast range is very short**  
**S:** Start by checking your antenna / wire connection (GPIO 4, pin 7). Then try using a longer antenna wire (17cm for 90MHz, adjust for your frequency). Consider using a band-pass filter and better antenna and avoid obstacles between transmitter and receiver.  
  
**I: I'm hearing interference or poor audio quality**  
**S:** Try using a clearer frequency without overlapping other stations if possible. Check your audio file (prefer 44.1kHz WAV files) and reduce transmission power by using a shorter antenna if the interference is severe.

**I: Files aren't uploading**  
**S:** Please do an issue.  
  
**I: The client keeps disconnecting**  
**S:** Check your network stability. If this persists, please open an issue.