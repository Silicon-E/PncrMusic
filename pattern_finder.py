"""A module for finding patterns within a given list of states"""


import powerset


MAXPATTERNLENGTH: int = 32
'The maximum number of ticks that a pattern can span'
MINPATTERNLENGTH: int = 6
'The minimum number of ticks that a pattern can span'

MAXPATTERNNOTES: int = 255
'The maximum number of notes that can be in a pattern if it is to be used'
MINPATTERNNOTES: int = 2
'The minimum number of notes that can be in a pattern if it is to be used'








class MusicSnippet:
	"""A class repersenting a sections of music via a list of sets, containing the events"""

	contained_section: list[set[tuple[int, int]]]
	"""
		The object that this is a wrapper for. The format is as follows:

		List, repersents the whole snippet, contains:
			Set, repersents one tick, contains:
				Tuple, repersents one music event, contains:
					Int, repersents the note value

					Int, repersents the length for which the note is played
	"""


	def __init__(self, contained_section: list[set[tuple[int, int]]]) -> None:
		self.contained_section = contained_section
	


	def subsection(self, start_index, end_index = -1):
		return MusicSnippet(self.contained_section[start_index, end_index])
	
	def findPatterns(self):

		for start_index in range(len(self.contained_section) - MINPATTERNLENGTH):
			for possible_pattern in powerset.semiordered_powerset(self.contained_section[start_index:start_index+MAXPATTERNLENGTH], True, MINPATTERNNOTES, MAXPATTERNNOTES, MINPATTERNLENGTH):
				matches: int = 0
				for check_index in range(len(self.contained_section) - len(possible_pattern)):
					for i, pattern_tick in enumerate(possible_pattern):
						if not (pattern_tick.issubset(self.contained_section[check_index+i])):
							break
					else:
						matches += 1
				
				if matches >= 4:
					yield possible_pattern



if __name__ == "__main__":
	example = MusicSnippet([{(1,2), (1,4)}, {}, {(1,2), (1,4), (1,3)}, {}, {(1,2), (1,4)}, {}, {(1,2), (1,4)}, {}, {(1,2), (1,4)}, {}, {(1,2), (1,4)}, {}])
	print(list(example.findPatterns())) # Currently returns [] This is wrong, and must be fixed
		
