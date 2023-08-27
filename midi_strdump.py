import mido as m
import sys

midi_filename = sys.argv[1]
mid: m.MidiFile = m.MidiFile(midi_filename)

note_offset = 18

music_sequence = []
conversion: float = 8 / mid.ticks_per_beat
print(mid.ticks_per_beat)
track = m.merge_tracks(mid.tracks)
i = 0
for msg in track:
	if (msg.type in {"note_on", "note_off"}):
		diff = '+' if msg.type=="note_on" else '-'
		note = msg.note + note_offset
		if note < 70:
			print(f' ..{msg.time}.. {diff}{note}')
			i += 1
			if i>=100:
				break