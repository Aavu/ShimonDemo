# Shimon Demo for Chicago Gig April 2022
**Shimon's Morning** \
Raga: Bahudari \
Key: D (Notes: D F# G A C D)

**Song Blueprint**
1. The following is done 3 times
   - Violin plays short phrase
   - Shimon responds
   - Keyboard plays short phrase
   - Shimon responds
2. Keyboard establishes tempo
   - Shimon listens for 16 beats
   - Shimon starts head bang
   - Keyboard ends playing
3. Verse
   - Shimon while headbanging, playing the low root note in tempo
   - Loops **verse1** in bahudari
   - Loops **verse2** if C#1 key is pressed
   - Loops **verse3** if D1 key is pressed
   - Loops **verse3** if D#1 key is pressed
   - Plays the korvai if E1 key is pressed


Installation:
note: use ```pip install --global-option='build_ext' --global-option='-I/opt/homebrew/include' --global-option='-L/opt/homebrew/lib' pyaudio``` on M1 Mac to install pyaudio after installing port audio using ```brew install portaudio```

Install the dependencies using environment.yml file
```conda env create -f environment.yml```