class Instrument:
    def __init__(self, name:str, note_min:int, note_max:int) -> None:
        self.name = name
        self.note_min = note_min
        self.note_max = note_max

        self.state_var = f"%music_{name}_state"
        self.pattern_var = f"%music_{name}_pattern"
        self.control_state_var = f"%music_{name}_control_state"
        self.pattern_state_var = f"%music_{name}_pattern_state"

        self.note_count = note_max - note_min + 1
        if self.note_count > 50:
            raise Exception(f'Note range f{note_min}..{note_max} has width {self.note_count}, which is greater than max bit count 50.')
        # Store as many bits as possible in the X of a variable. Only store some in Z.
        self.bits_stored_in_x = min(25, self.note_count)
        self.bits_stored_in_z = max(0, self.note_count - self.bits_stored_in_x)
    
    def note_to_axis_and_bit(self, note:int) -> tuple[int,int]:
        if note < self.note_min or note > self.note_max:
            return (1,0)
            #raise Exception(f'Note {note} not in instrument range {self.note_min}..{self.note_max}')

        axis = 0
        bit = 24 - (note - self.note_min)
        if bit < self.bits_stored_in_z:
            offset = self.bits_stored_in_z - bit
            bit = self.bits_stored_in_z - ((offset - 1) // 2 + 1)
            axis = 0 if offset % 2 == 1 else 2
        return (axis, bit)

    def encode_state(self, notes_on) -> tuple[int,int,int]:
        state = [0,0,0]
        for note in notes_on:
            axis, bit = self.note_to_axis_and_bit(note)
            state[axis] |= 1 << bit
        return tuple(state)
    
    def decode_state(self, state: tuple[int,int,int]) -> set:
        result = set()
        
        bit = 24
        note = whistle.note_min
        while note <= whistle.note_max:
            if state[0] & (1 << bit) > 0:
                result.add(note)

            if bit < whistle.bits_stored_in_z:
                note += 1
                if state[2] & (1 << bit) > 0:
                    result.add(note)

            bit -= 1
            note += 1
        
        return result

whistle = Instrument('whistle', 54, 89 + 12)

print(whistle.encode_state([54, 66]))