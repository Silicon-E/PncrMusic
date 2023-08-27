"""Pneumaticraft data helper module. Useful for generating Pneumaticraft programs."""

piece_height = 11
piece_width  = 15

def nbt(type:int, value) -> dict:
    return {
        "type": type,
        "value": value
    }

class Program:
    """An interface for generating Pneumaticraft programs."""

    def __init__(self) -> None:
        self.pieces = []
        self.current_pos = (0,0)

    def begin_block(self):
        self.current_pos = (20 - self.current_pos[0], self.current_pos[1] + 3)

    def feed(self, n = 1):
        self.current_pos = (self.current_pos[0], self.current_pos[1] + n * piece_height)

    def put_piece(self, opcode:str, pos:tuple[int], extra_data:dict = {}):
        global pieces
        self.pieces.append({
            "name": nbt(8, opcode),
            "x":    nbt(3, pos[0]),
            "y":    nbt(3, pos[1])
        } | extra_data)

    def add_piece(self, opcode:str, extra_data:dict = {}, sockets:list[tuple[list[tuple]]] = [([],[])]):
        '''sockets: list of rows.
        row: tuple of (left wing, right wing).
        wing: list of (opcode) and/or (opcode, extra_data)'''

        self.put_piece(opcode, self.current_pos, extra_data)
        for i, row in enumerate(sockets):
            pass # TODO

        self.feed(max(1, len(sockets)))

    def add_simple(self, opcode: str, string: str):
        self.put_piece(opcode, self.current_pos)
        self.put_piece('text', (self.current_pos[0]+piece_width, self.current_pos[1]), {
            "string": nbt(8, string)
        })
        self.feed()

    def add_wait(self, ticks: int):
        self.add_simple('wait', ticks-3)

    def add_operator(self, variable:str, operator:int, left:list, right:list):
        self.put_piece("coordinate_operator", self.current_pos, {
            "variable": nbt(8, variable),
            "checkX":   nbt(1, 1),
            "checkY":   nbt(1, 1),
            "checkZ":   nbt(1, 1),
            "operator": nbt(1, operator)
        })
        def put(item, x_offset):
            if type(item) is str:
                self.put_piece('coordinate', (self.current_pos[0]+x_offset, self.current_pos[1]), {
                    "useVariable": nbt(1, 1),
                    "coord": nbt(10, {
                        "X": nbt(3, 0),
                        "Y": nbt(3, 0),
                        "Z": nbt(3, 0)
                    }),
                    "variable": nbt(8, item),
                })
            else: # is tuple
                self.put_piece('coordinate', (self.current_pos[0]+x_offset, self.current_pos[1]), {
                    "useVariable": nbt(1, 0),
                    "coord": nbt(10, {
                        "X": nbt(3, item[0]),
                        "Y": nbt(3, item[1]),
                        "Z": nbt(3, item[2])
                    }),
                    "variable": nbt(8, ""),
                })
        
        i = -1
        for item in left:
            put(item, i*piece_width)
            i -= 1
        i = 1
        for item in right:
            put(item, i*piece_width)
            i += 1

        self.feed()