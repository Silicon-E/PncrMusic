"""Finds the power set (all possible subsets)"""
import math as m
import collections.abc

def powerset(s: set) -> collections.abc.Generator[set, None, None]:
	# There are 2^n subsets, so we iterate through all of them
	for combination in range(2 ** len(s)):
		out: set = set()

		# For every output, we must determine whether each thing is added or not
		for j, item in enumerate(s):
			# Each bit in "combination" repersents whether or not one of the items is used, so we check each bit by
			# doing a bitwise and with 2^(the number bit we want to check)
			if (2 ** j) & combination > 0:
				# If the bit is 1, add the item
				out.add(item)

		yield out

def semiordered_powerset(l: list[set[int]], fill_first_set:bool = True, min_notes:int = 0, max_notes:int = 16, min_length:int = 0) -> collections.abc.Generator[list[set], None, None]:
	"""This will perform a power set operation on all of the sets contained in l, combined, 
	but treat each value stored at a different index seperately. Note that this method has
	a bunch of weird options because it is very specialized, and must also be extremely fast."""
	total_count: int = 0

	# Count the number elements in all the sets
	for s in l:
		total_count += len(s)
	
	# Needs to skip all possibilities with a length < min_length

	for i in range(2 ** total_count):
		# This is a really fast way of checking if the bits in the first tick are 0, becasue if they are, we can skip this cycle
		if fill_first_set and (i & (2 ** len(l[0]) - 1)) == 0:
			continue

		if min_notes != 0 and (i.bit_count() < min_notes):
			continue
		if i.bit_count() > max_notes:
			continue

		#print(bin(i)[2:])
		# This variable accounts for the past ticks as far as what bit to check
		total_set_count: int = 0
		out: list[set] = []
		

		for j, set_ in enumerate(l):
			out_set: set = set()

			for k, element in enumerate(set_):
				if (2 ** (j + k + total_set_count)) & i > 0:
					out_set.add(element)
			
			total_set_count += len(set_) - 1

			out.append(out_set)
		
		yield out



if __name__ == "__main__":
	print(list(semiordered_powerset([{1, 2}, {3,4}])))