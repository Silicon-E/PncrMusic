import json
import math
import pncr
from pncr_music import whistle




# Add the pieces.
program = pncr.Program()

program.begin_block()
program.add_piece('start')
# program.add_operator("state", 0, [], [whistle.state_var, whistle.control_state_var])
program.add_operator("state", 0, [], [whistle.state_var, "nonpattern"])
program.add_operator("nonpattern", 0, [], [whistle.control_state_var])

bit = 24
note = whistle.note_min
jump = 0
while note <= whistle.note_max:
    scale = 1 << bit

    note1_var = f"%music_whistle_{note}"
    program.add_operator(note1_var, 1, [(scale,1,scale)], ["state"])
    program.add_operator(note1_var, 1, [],                [note1_var, (scale,1,scale)])
    program.add_operator("state",  0, [note1_var], ["state"])

    if bit < whistle.bits_stored_in_z:
        note += 1
        note2_var = f"%music_whistle_{note}"

        program.add_operator(note2_var, 0, [], [(0,0,0)])

        program.put_piece("condition_coordinate", program.current_pos, {
            "checkX": pncr.nbt(1, 0.0),
            "checkY": pncr.nbt(1, 0.0),
            "checkZ": pncr.nbt(1, 1.0),
            "operator": pncr.nbt(1, 0.0)
        })
        program.put_piece('coordinate', (program.current_pos[0]+pncr.piece_width, program.current_pos[1]), {
            "useVariable": pncr.nbt(1, 1),
            "coord": pncr.nbt(10, {
                "X": pncr.nbt(3, 0),
                "Y": pncr.nbt(3, 0),
                "Z": pncr.nbt(3, 0)
            }),
            "variable": pncr.nbt(8, note1_var),
        })
        program.put_piece('text', (program.current_pos[0]+pncr.piece_width, program.current_pos[1]+pncr.piece_height*2), {
            "string": pncr.nbt(8, f"jump_{jump}")
        })
        program.feed(3)

        program.add_operator(note2_var, 0, [], [(15,0,0)])

        if note < whistle.note_max:
            program.put_piece('jump', program.current_pos)
            program.put_piece('text', (program.current_pos[0]+pncr.piece_width, program.current_pos[1]), {
                "string": pncr.nbt(8, f"jump_{jump}")
            })
            program.feed()

        program.begin_block()

        program.put_piece('label', program.current_pos)
        program.put_piece('text', (program.current_pos[0]+pncr.piece_width, program.current_pos[1]), {
            "string": pncr.nbt(8, f"jump_{jump}")
        })
        program.feed()

        # We have to add a piece to the last jump label to prevent compile errors.
        if note == whistle.note_max:
            program.add_operator("state", 0, [], [])

        jump += 1

    bit -= 1
    note += 1


# Write the program to a file.
output = {
    "pneumaticcraft:progWidgets": {
        "type": 9,
        "value": program.pieces
    }
}

with open(f'{whistle.name}_state_decoder.json', '+w') as file:
    file.write(json.dumps(output))