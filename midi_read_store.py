import mido as m
import sys
import os
import pncr
import pncr_music
import json


SOFT_MAX_FILE_LENGTH: int = 300000


class MusicEvent:
	def __init__(self, state:tuple[int,int,int]) -> None:
		self.state = state

	def block_count(self) -> int:
		return 2

	# Define functions needed to use this as a key object.
	def __hash__(self):
		return hash(self.state)
	def __eq__(self, other):
		return isinstance(self, MusicEvent) and isinstance(other, MusicEvent) and self.state == other.state

class MusicWait:
	def __init__(self, mc_ticks : int) -> None:
		self.mc_ticks = int(mc_ticks)
	
	# Define functions needed to use this as a key object.
	def __hash__(self):
		return hash(self.mc_ticks)
	def __eq__(self, other):
		return isinstance(self, MusicWait) and isinstance(other, MusicWait) and self.mc_ticks == other.mc_ticks
	
	def block_count(self) -> int:
		return 2

class Pattern:
	def __init__(self, sequence: list) -> None:
		self.sequence = sequence
		self.mc_ticks = 0
		for event in sequence:
			if isinstance(event, MusicWait):
				self.mc_ticks += event.mc_ticks
	
	# Define functions needed to use this as a key object.
	def __hash__(self):
		return hash(tuple(self.sequence))
	def __eq__(self, other):
		return isinstance(self, Pattern) and isinstance(other, Pattern) and self.sequence == other.sequence

	def block_count(self) -> int:
		result = 2
		for event in self.sequence:
			result += event.block_count()
		return result

class MusicPattern:
	def __init__(self, pattern: Pattern) -> None:
		self.pattern = pattern
	
	# Define functions needed to use this as a key object.
	def __hash__(self):
		result = 0b0
		for event in self.pattern.sequence:
			result ^= hash(event)
		return result
	def __eq__(self, other):
		return isinstance(self, MusicPattern) and isinstance(other, MusicPattern) and self.pattern == other.pattern

	def block_count(self) -> int:
		return 2

def count_blocks(sequence : list, patterns : list[MusicPattern]) -> int:
	result = sum(event.block_count() for event in sequence)
	for pattern in patterns:
		result += pattern.block_count()
	return result

# Convert the MIDI file to a sequence of MusicEvents and MusicWaits.
# midi_filename = './soul_sanctum_multitrack.mid'
# ticks_per_measure = 3 * 8

midi_filename = './No_Time_For_Caution_Interstellar.mid'
ticks_per_measure = 3 * 8

#midi_filename = sys.argv[1]
end_wait = ticks_per_measure * 4

mid: m.MidiFile = m.MidiFile(midi_filename)

tracks = []
conversion: float = ticks_per_measure/8 * 2 / mid.ticks_per_beat
print(mid.ticks_per_beat)
note_offset = 18
'An offset, in semitones, that should be applied to the pitch of each note in the song.'
instrument = pncr_music.whistle
for pattern_id in range(len(mid.tracks)):
	src_track = mid.tracks[pattern_id]
	dst_track = []
	notes_active = set()
	prev_notes_active = None

	for msg in src_track:
		if (msg.type in {"note_on", "note_off"}):
			if (msg.time > 0):
				if notes_active != prev_notes_active:
					prev_notes_active = notes_active.copy()
					dst_track.append(MusicEvent(instrument.encode_state(notes_active)))
				dst_track.append(MusicWait(msg.time * conversion))
			
			note = msg.note + note_offset
			if msg.type == "note_on":
				notes_active.add(note)
			elif note in notes_active:
				notes_active.remove(note)
	if notes_active != prev_notes_active:
		dst_track.append(MusicEvent(instrument.encode_state(notes_active)))
	
	if len(dst_track) > 1:
		tracks.append(dst_track)


# Remove notes from the first track wherever that note is duplicated by another track.
# This prevents carry-bit errors from adding the control state tuple to the pattern state tuple.
# (The tuples are added to achieve the effect of a bitwise OR.)
def track_events_by_time(tracks: list[list]) -> dict[int, list[list]]:
	"""Given a list of tracks (lists of events), returns a map from: time -> track idx -> list of events on [track] at [time].
	MusicWait objects are not included."""
	time_to_track_to_events = dict()
	for pattern_id, track in enumerate(tracks):
		time = 0
		for music_obj in track:
			if isinstance(music_obj, MusicWait):
				time += music_obj.mc_ticks
			else:
				if time not in time_to_track_to_events:
					time_to_track_to_events[time] = dict()
				track_to_music_objs = time_to_track_to_events[time]
				if pattern_id not in track_to_music_objs:
					track_to_music_objs[pattern_id] = []
				track_to_music_objs[pattern_id].append(music_obj)
	return time_to_track_to_events

def track_events(time_to_track_to_events: dict[int, list[list]], merge_tracks = False):
	"""Given a map returned by track_events_by_time(), returns a list of tracks.
	If merge_tracks==True, returns a single track."""
	prev_time = 0
	track_to_prev_time = {i: 0 for i in range(len(tracks))}
	result = []
	track_to_state = {i: (0,0,0) for i in range(len(tracks))}
	for time in sorted(time_to_track_to_events.keys()):
		if merge_tracks:
			prev_state = None
			track = result

			if time - prev_time > 0:
				track.append(MusicWait(time - prev_time))
			
			for track_idx, music_objs in time_to_track_to_events[time].items():
				for music_obj in music_objs:
					if isinstance(music_obj, MusicEvent):
						track_to_state[track_idx] = music_obj.state
					else:
						track.append(music_obj)
			
			state = (0,0,0)
			for track_state in track_to_state.values():
				state = (state[0] | track_state[0], state[1] | track_state[1], state[2] | track_state[2])
			if state != prev_state:
				track.append(MusicEvent(state))
				prev_state = state
		
			prev_time = time
		else:
			track_to_prev_state = track_to_state.copy()
			
			for track_idx, music_objs in time_to_track_to_events[time].items():
				while len(result)-1 < track_idx:
					result.append([])
				track = result[track_idx]

				if len(music_objs) > 0:
					if time - track_to_prev_time[track_idx] > 0:
						track.append(MusicWait(time - track_to_prev_time[track_idx]))

					for music_obj in music_objs:
						if isinstance(music_obj, MusicEvent):
							track_to_state[track_idx] = music_obj.state
						else:
							track.append(music_obj)
				
					track_state = track_to_state[track_idx]
					if track_state != track_to_prev_state[track_idx]:
						track.append(MusicEvent(track_state))
						track_to_prev_state[track_idx] = track_state
				
					track_to_prev_time[track_idx] = time
		
	return result

if len(tracks) > 1:
	time_to_track_to_events = track_events_by_time(tracks)

	track_to_state = {i: (0,0,0) for i in range(len(tracks))}
	for time in sorted(time_to_track_to_events.keys()):
		for track_idx, music_objs in time_to_track_to_events[time].items():
			if track_idx > 0:
				music_objs = time_to_track_to_events[time][track_idx]
				for music_obj in music_objs:
					if isinstance(music_obj, MusicEvent):
						track_to_state[track_idx] = music_obj.state
		
		nonfirst_state = (0,0,0)
		for track_idx in range(1, len(tracks)):
			track_state = track_to_state[track_idx]
			nonfirst_state = (nonfirst_state[0] | track_state[0], nonfirst_state[1] | track_state[1], nonfirst_state[2] | track_state[2])

		for music_obj in time_to_track_to_events[time][0]:
			if isinstance(music_obj, MusicEvent):
				music_obj.state = tuple([music_obj.state[i] & ~nonfirst_state[i] for i in range(3)])

	tracks = track_events(time_to_track_to_events)


# Debug output
for track in tracks:
	print(f'Blocks before optimizing: {count_blocks(track, [])}')


# Compress measures in the first track into patterns.
measure_to_count = dict()
first_track = tracks[0]
time = 0
measures: list[Pattern] = []
current_measure = []
for pattern_id in range(len(first_track)):
	event = first_track[pattern_id]
	current_measure.append(event)

	if isinstance(event, MusicWait):
		time += event.mc_ticks
	# Push the current measure once we reach the next one, or at the end of the thread.
	if time >= ticks_per_measure or pattern_id == len(first_track)-1:
		time -= ticks_per_measure
		measure_pattern = Pattern(current_measure)
		current_measure = []
		measures.append(measure_pattern)
		if measure_pattern not in measure_to_count:
			measure_to_count[measure_pattern] = 0
		measure_to_count[measure_pattern] += 1

patterns = []
pattern_to_id = dict()
max_patterns = 100
for measure, count in sorted(measure_to_count.items(), key=lambda item: item[1], reverse=True):
	# Don't create patterns for measures that occur only once.
	if count <= 1 or len(patterns) >= max_patterns:
		break
	pattern_to_id[measure] = len(patterns)
	patterns.append(measure)

# Turn the sequence of measures back into a track. Replace measures with patterns where appropriate.
first_track.clear()
for measure in measures:
	if measure in pattern_to_id:
		first_track.append(MusicPattern(measure))
		first_track.append(MusicWait(measure.mc_ticks))
	else:
		for event in measure.sequence:
			first_track.append(event)


# Debug output
for track in tracks:
	pattern_list = patterns if track==first_track else []
	print(f'Blocks after optimizing:  {count_blocks(track, pattern_list)}')


# Merge all sequences of Music objects.
time_to_track_to_music_objs = track_events_by_time(tracks)
			
track = []
prev_time = 0
prev_state = None
track_to_state = {i: (0,0,0) for i in range(len(tracks))}
for time in sorted(time_to_track_to_music_objs.keys()):
	if time - prev_time > 0:
		track.append(MusicWait(time - prev_time))
	
	for track_idx, music_objs in time_to_track_to_music_objs[time].items():
		for music_obj in music_objs:
			if isinstance(music_obj, MusicEvent):
				track_to_state[track_idx] = music_obj.state
			else:
				track.append(music_obj)
	
	state = (0,0,0)
	for track_state in track_to_state.values():
		state = (state[0] | track_state[0], state[1] | track_state[1], state[2] | track_state[2])
	if state != prev_state:
		track.append(MusicEvent(state))
		prev_state = state
	
	prev_time = time


# Debug output
def sequence_summary(sequence):
	result = ''
	for music_obj in sequence:
		if isinstance(music_obj, MusicWait):
			result += f' ..{int(music_obj.mc_ticks)}..'
		elif isinstance(music_obj, MusicEvent):
			result += f' {instrument.decode_state(music_obj.state)}'
		elif isinstance(music_obj, MusicPattern):
			result += f' [{sequence_summary(music_obj.pattern.sequence)}]'
	return result
with open('./midi_read_store_summary.txt', '+w') as file:
	file.write(sequence_summary(track))


def sequence_to_assigns(sequence) -> list:
	global pattern_to_id

	assigns = []
	current = [(0,-1,0), 0]
	for event in sequence:
		if isinstance(event, MusicWait):
			current[1] += event.mc_ticks
			if current[1] > 0:
				assigns.append(tuple(current))
				current = [(current[0][0], -1, current[0][2]), 0]
		elif isinstance(event, MusicEvent):
			current[0] = (event.state[0], current[0][1], event.state[2])
		elif isinstance(event, MusicPattern):
			current[0] = (current[0][0], pattern_to_id[event.pattern], current[0][2])
	if current[1] > 0:
		assigns.append(tuple(current))
	return assigns

def assigns_dump_pieces(program, output_var, assigns):
	for assign in assigns:
		program.add_operator(output_var, 0, [], [assign[0]])
		program.add_wait(assign[1])

		if program.current_pos[1] > pncr.piece_height * 1000:
			raise Exception('Too many pieces!')


# Format the sequence of Music... objects as JSON.
def dump_pieces(program, output_var, music_obj):
	global notes_active
	global instrument

	if isinstance(music_obj, MusicWait):
		program.add_wait(music_obj.mc_ticks)
	elif isinstance(music_obj, MusicEvent):
		program.add_operator(output_var, 0, [], [music_obj.state])
	elif isinstance(music_obj, MusicPattern):
		program.add_operator(instrument.pattern_var, 0, [], [(pattern_to_id[music_obj.pattern], 0, 0)])
		program.add_wait(music_obj.pattern.mc_ticks)

pattern_program = pncr.Program()
pattern_program.begin_block()
pattern_program.add_piece('start')
pattern_program.add_simple('jump', 'loop')

pattern_program.begin_block()
pattern_program.add_simple('label', 'loop')
for pattern_id, pattern in enumerate(patterns):
	pattern_program.put_piece("condition_coordinate", pattern_program.current_pos, {
		"checkX": pncr.nbt(1, 0.0),
		"checkY": pncr.nbt(1, 1.0),
		"checkZ": pncr.nbt(1, 0.0),
		"operator": pncr.nbt(1, 0.0)
	})
	pattern_program.put_piece('coordinate', (pattern_program.current_pos[0]+pncr.piece_width, pattern_program.current_pos[1]), {
		"useVariable": pncr.nbt(1, 1),
		"coord": pncr.nbt(10, {
			"X": pncr.nbt(3, 0),
			"Y": pncr.nbt(3, 0),
			"Z": pncr.nbt(3, 0)
		}),
		"variable": pncr.nbt(8, instrument.control_state_var),
	})
	pattern_program.put_piece('coordinate', (pattern_program.current_pos[0]-pncr.piece_width, pattern_program.current_pos[1]), {
		"useVariable": pncr.nbt(1, 0),
		"coord": pncr.nbt(10, {
			"X": pncr.nbt(3, 0),
			"Y": pncr.nbt(3, pattern_id),
			"Z": pncr.nbt(3, 0)
		}),
		"variable": pncr.nbt(8, ''),
	})
	pattern_program.put_piece('text', (pattern_program.current_pos[0]+pncr.piece_width, pattern_program.current_pos[1]+pncr.piece_height*2), {
		"string": pncr.nbt(8, f"pattern_{pattern_id}")
	})
	pattern_program.feed(3)
pattern_program.add_operator(instrument.state_var, 0, [], [(0,0,0)])

for pattern_id, pattern in enumerate(patterns):
	pattern_program.begin_block()
	pattern_program.add_simple('label', f'pattern_{pattern_id}')
	for event in pattern.sequence:
		dump_pieces(pattern_program, instrument.state_var, event)
	pattern_program.add_simple('jump', 'loop')

program = pncr.Program()
program.begin_block()
program.add_piece('start')
assigns_dump_pieces(program, instrument.control_state_var, sequence_to_assigns(track))
if end_wait > 0:
	program.add_operator(instrument.control_state_var, 0, [], [(0,-1,0)])
	program.add_wait(end_wait)


pattern_decoder = {
	"pneumaticcraft:progWidgets": {
		"type": 9,
		"value": pattern_program.pieces
	}
}
output = {
	"pneumaticcraft:progWidgets": {
		"type": 9,
		"value": program.pieces
	}
}

with open(f"program_pattern_{os.path.basename(midi_filename).replace('.mid', '')}.json", '+w') as file:
	file.write(json.dumps(pattern_decoder))

outputJson = json.dumps(output)
isMultiFile: bool = False
fileNumber: int = 1

def finalized_json(json: str):
	return json # """{"pneumaticcraft:progWidgets":{"type":9,"value":[{"name":{"type":8,"value":"start"},"x":{"type":3,"value":0.0},"y":{"type":3,"value":0.0}}""" + json + "]}}"

# Write the produced JSON to an output file.
def finalize_and_save_json_chunk(fileTag: str):
	with open(f"program_{os.path.basename(midi_filename).replace('.mid', '')}{fileTag}.json", "+w") as file:
		file.write(finalized_json(outputJson))

# for music_obj in music_sequence:
# 	dump_json(music_obj)

# 	if len(outputJson) >= SOFT_MAX_FILE_LENGTH:
# 		finalize_and_save_json_chunk(str(fileNumber))

# 		isMultiFile = True
# 		fileNumber += 1
# 		outputJson = ""


if isMultiFile:
	finalize_and_save_json_chunk(str(fileNumber))
	outputJson = """{"pneumaticcraft:progWidgets":{"type":9,"value":[{"name":{"type":8,"value":"start"},"x":{"type":3,"value":5.0},"y":{"type":3,"value":11.0}},{"name":{"type":8,"value":"external_program"},"x":{"type":3,"value":5.0},"y":{"type":3,"value":33.0}},{"name":{"type":8,"value":"coordinate_operator"},"x":{"type":3,"value":5.0},"variable":{"type":8,"value":"targetLocation"},"checkX":{"type":1,"value":1.0},"y":{"type":3,"value":22.0},"checkY":{"type":1,"value":1.0},"checkZ":{"type":1,"value":1.0},"operator":{"type":1,"value":0.0}},{"name":{"type":8,"value":"area"},"x":{"type":3,"value":20.0},"y":{"type":3,"value":33.0},"pos1":{"type":10,"value":{"X":{"type":3,"value":0.0},"Y":{"type":3,"value":0.0},"Z":{"type":3,"value":0.0}}},"pos2":{"type":10,"value":{"X":{"type":3,"value":0.0},"Y":{"type":3,"value":0.0},"Z":{"type":3,"value":0.0}}},"boxType":{"type":1,"value":0.0},"type":{"type":8,"value":"box"},"var2":{"type":8,"value":"targetLocation"},"var1":{"type":8,"value":"targetLocation"}},{"useVariable":{"type":1,"value":1.0},"coord":{"type":10,"value":{"X":{"type":3,"value":0.0},"Y":{"type":3,"value":0.0},"Z":{"type":3,"value":0.0}}},"name":{"type":8,"value":"coordinate"},"x":{"type":3,"value":20.0},"variable":{"type":8,"value":"$controller_pos"},"y":{"type":3,"value":22.0}},{"coord":{"type":10,"value":{"X":{"type":3,"value":0.0},"Y":{"type":3,"value":-1.0},"Z":{"type":3,"value":0.0}}},"name":{"type":8,"value":"coordinate"},"x":{"type":3,"value":35.0},"y":{"type":3,"value":22.0}}]}}""" #TODO add external program stuff here
	finalize_and_save_json_chunk("MASTER")
else:
	finalize_and_save_json_chunk("")