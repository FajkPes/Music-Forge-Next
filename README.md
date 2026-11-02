# Music Forge Next

A local music generator that turns a style, mood and seed into an editable instrumental track.

## What is it for?

Music Forge Next creates instrumental music locally from a seed, style and mood. It is designed for exploring ideas and changing the result in a mixer without an online account, a cloud model or a full digital audio workstation.

## Features

- Choose from 58 styles and 24 moods, with durations from 20 seconds to 10 minutes.
- Generate a full track or a 30-second preview; reuse the seed to reproduce a composition.
- Change instruments and adjust volume, pan, mute, solo, brightness, saturation and space per track.
- Export 48 kHz stereo WAV, Opus or MIDI, and save the settings as an editable project.
- Sound banks are included in the Windows release; the app also contains synthetic presets.

## Install and start on Windows

1. Install Python 3.12 x64 and download the complete ZIP from [Releases](https://github.com/FajkPes/Music-Forge-Next/releases/latest).
2. Extract the ZIP and run `Nainstalovat.cmd`. This creates a local Python environment and downloads the required packages.
3. Run `Spustit Music Forge.cmd` and leave the server window open while using the app.
4. Pick a seed, style and mood, then generate a preview or track. Adjust the mixer and export from the player.

After setup, music generation works locally. The interface is currently in Czech. The public package excludes the private research library, so its research track list is empty. It creates instrumental music and does not host VST plugins or generate singing.

Sound-bank licenses and attribution, including the Salamander piano credit, are included with the package. See [README-DETAILS.md](README-DETAILS.md) for the original detailed notes.

[Detailed documentation](README-DETAILS.md) · [All releases](https://github.com/FajkPes/Music-Forge-Next/releases)

## Explore variations and control the mix

The seed is a way to return to a generated composition. **New motif** changes the main melody while preserving other notes; **New sounds** changes the automatic instrument palette while keeping the score and manually chosen instruments. The arrangement uses roles such as drums, bass, chords, lead, atmosphere and transitions, which can pause in quieter sections. Mix changes such as volume and pan respond during playback; changing an instrument reloads that track. A saved project stores settings and seeds rather than the finished audio, so export WAV or Opus when you need an audio file.

## Credits

**Idea, concept and design:** FajkPes  
**Coding:** ChatGPT Codex, Claude and Google Antigravity
