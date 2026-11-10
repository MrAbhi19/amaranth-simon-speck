# Copyright 2026 MrAbhi19
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from amaranth import *
from amaranth.sim import Simulator

def f_x(x):
    s1_x = x.rotate_left(1)
    s8_x = x.rotate_left(8)
    s2_x = x.rotate_left(2)

    return (s1_x & s8_x) ^ s2_x

def simon_round_fun(x, y, k):
    new_x = y ^ f_x(x) ^ k
    new_y = x
    return new_x, new_y

def simon_inv_round_func(x, y, k):
    new_x = y
    new_y = x ^ f_x(y) ^ k
    return new_x, new_y

class ExpandKey(Elaboratable):
    def __init__(self, N=32, M=4, T=44, J=3):
        self.N = N
        self.M = M
        self.T = T
        self.J = J

        self.key_in = Signal(N * M)
        self.key_out = Signal(N * T)

    def elaborate(self, platform):
        m = Module()

        N, M, T, J = self.N, self.M, self.T, self.J

        # Simon Z sequences (62 bits each, read left to right)
        Z_SEQ = [
            "11111010001001010110000111001101111101000100101011000011100110",
            "10001110111110010011000010110101000111011111001001100001011010",
            "10101111011100000011010010011000101000010001111110010110110011",
            "11011011101011000110010111100000010010001010011100110100001111",
            "11010001111001101011011000100000010111000011001010010011101111"
        ]

        # c=2n−4=0xff···fc.
        c = Const((1 << N) - 4, N)

        key = [Signal(N, name=f"key_{i}") for i in range(T)]

        for i in range(M):
            m.d.comb += key[i].eq(self.key_in[i*N : (i+1)*N])

        for i in range(M, T):
            tmp = key[i-1].rotate_right(3)

            if M == 4:
                tmp = tmp ^ key[i - 3]

            tmp = tmp ^ tmp.rotate_right(1)

            # Get the single bit from the chosen Z sequence for this round
            z_val = int(Z_SEQ[J][(i - M) % 62])
            z_bit = Const(z_val, 1)

            m.d.comb += key[i].eq(key[i - M] ^ tmp ^ c ^ z_bit)

        for i in range(T):
            m.d.comb += self.key_out[i*N : (i+1)*N].eq(key[i])

        return m

class Encrypt(Elaboratable):
    def __init__(self, N=32, M=4, T=44, J=3):
        self.N = N
        self.M = M
        self.T = T
        self.J = J

        self.data_in = Signal(2*N)
        self.key = Signal(N*M)
        self.data_out = Signal(2*N)

    def elaborate(self, platform):
        m = Module()
        m.submodules.expand = expand = ExpandKey(self.N, self.M, self.T, self.J)

        m.d.comb += expand.key_in.eq(self.key)

        N, M, T, J = self.N, self.M, self.T, self.J

        x = [Signal(N, name=f"x_{i}") for i in range(T + 1)]
        y = [Signal(N, name=f"y_{i}") for i in range(T + 1)]

        m.d.comb += [
            x[0].eq(self.data_in[N : 2* N]),
            y[0].eq(self.data_in[0 : N])
            ]

        for i in range(T):
            round_key = expand.key_out[i*N : (i+1)*N]

            nx, ny = simon_round_fun(x[i], y[i], round_key)

            m.d.comb += [
                x[i+1].eq(nx),
                y[i+1].eq(ny)
            ]

        m.d.comb += self.data_out.eq(Cat(y[T], x[T]))

        return m


class Decrypt(Elaboratable):
    def __init__(self, N=32, M=4, T=44, J=3):
        self.N = N
        self.M = M
        self.T = T
        self.J = J

        self.data_in = Signal(2*N)
        self.key = Signal(N*M)
        self.data_out = Signal(2*N)

    def elaborate(self, platform):
        m = Module()
        m.submodules.expand = expand = ExpandKey(self.N, self.M, self.T, self.J)

        m.d.comb += expand.key_in.eq(self.key)

        N, M, T, J = self.N, self.M, self.T, self.J

        x = [Signal(N, name=f"x_{i}") for i in range(T + 1)]
        y = [Signal(N, name=f"y_{i}") for i in range(T + 1)]

        m.d.comb += [
            x[0].eq(self.data_in[N : 2* N]),
            y[0].eq(self.data_in[0 : N])
            ]

        for j in range(T):
            rk = T - 1 - j

            round_key = expand.key_out[rk*N : (rk+1)*N]

            nx, ny = simon_inv_round_func(x[j], y[j], round_key)

            m.d.comb += [
                x[j+1].eq(nx),
                y[j+1].eq(ny)
            ]

        m.d.comb += self.data_out.eq(Cat(y[T], x[T]))

        return m

# =====================================================================
# VERIFICATION
# =====================================================================
# The following code, including the test vectors and simulation setup,
# is strictly for testing and verifying the correctness of the crypto core.
# It is not required for hardware synthesis or integration into larger designs.
# =====================================================================

SIMON_VARIANTS = [
    {
        "name": "Simon32/64",
        "N": 16, "M": 4, "T": 32, "J": 0,
        "key": 0x1918111009080100,
        "pt":  0x65656877,
        "ct":  0xc69be9bb
    },
    {
        "name": "Simon48/72",
        "N": 24, "M": 3, "T": 36, "J": 0,
        "key": 0x1211100a0908020100,
        "pt":  0x6120676e696c,
        "ct":  0xdae5ac292cac
    },
    {
        "name": "Simon48/96",
        "N": 24, "M": 4, "T": 36, "J": 1,
        "key": 0x1a19181211100a0908020100,
        "pt":  0x72696320646e,
        "ct":  0x6e06a5acf156
    },
    {
        "name": "Simon64/96",
        "N": 32, "M": 3, "T": 42, "J": 2,
        "key": 0x131211100b0a090803020100,
        "pt":  0x6f7220676e696c63,
        "ct":  0x5ca2e27f111a8fc8
    },
    {
        "name": "Simon64/128",
        "N": 32, "M": 4, "T": 44, "J": 3,
        "key": 0x1b1a1918131211100b0a090803020100,
        "pt":  0x656b696c20646e75,
        "ct":  0x44c8fc20b9dfa07a
    },
    {
        "name": "Simon96/96",
        "N": 48, "M": 2, "T": 52, "J": 2,
        "key": 0x0d0c0b0a0908050403020100,
        "pt":  0x2072616c6c69702065687420,
        "ct":  0x602807a462b469063d8ff082
    },
    {
        "name": "Simon96/144",
        "N": 48, "M": 3, "T": 54, "J": 3,
        "key": 0x1514131211100d0c0b0a0908050403020100,
        "pt":  0x74616874207473756420666f,
        "ct":  0xecad1c6c451e3f59c5db1ae9
    },
    {
        "name": "Simon128/128",
        "N": 64, "M": 2, "T": 68, "J": 2,
        "key": 0x0f0e0d0c0b0a09080706050403020100,
        "pt":  0x63736564207372656c6c657661727420,
        "ct":  0x49681b1e1e54fe3f65aa832af84e0bbc
    },
    {
        "name": "Simon128/192",
        "N": 64, "M": 3, "T": 69, "J": 3,
        "key": 0x17161514131211100f0e0d0c0b0a09080706050403020100,
        "pt":  0x206572656874206e6568772065626972,
        "ct":  0xc4ac61effcdc0d4f6c9c8d6e2597b85b
    },
    {
        "name": "Simon128/256",
        "N": 64, "M": 4, "T": 72, "J": 4,
        "key": 0x1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100,
        "pt":  0x74206e69206d6f6f6d69732061207369,
        "ct":  0x8d2b5579afc8a3a03bf72a87efe7b868
    }
]

def verify_variant(variant):
    """Dynamically creates a module for a variant and tests it."""
    N, M = variant["N"], variant["M"]
    T, J = variant["T"], variant["J"]

    # Instantiate the Simon modules
    enc = Encrypt(N=N, M=M, T=T, J=J)
    dec = Decrypt(N=N, M=M, T=T, J=J)

    m = Module()
    m.submodules.enc = enc
    m.submodules.dec = dec

    # Wire outputs directly to inputs to test the round-trip
    m.d.comb += [
        dec.key.eq(enc.key),
        dec.data_in.eq(enc.data_out)
    ]

    async def testbench(ctx):
        ctx.set(enc.data_in, variant["pt"])
        ctx.set(enc.key, variant["key"])

        actual_ct = ctx.get(enc.data_out)
        actual_pt = ctx.get(dec.data_out)

        assert actual_ct == variant["ct"], \
            f"Encrypt failed for {variant['name']}: expected {hex(variant['ct'])}, got {hex(actual_ct)}"

        assert actual_pt == variant["pt"], \
            f"Decrypt failed for {variant['name']}: expected {hex(variant['pt'])}, got {hex(actual_pt)}"

        print(f"Verified {variant['name']}")

    sim = Simulator(m)
    sim.add_testbench(testbench)
    sim.run()

if __name__ == "__main__":
    for v in SIMON_VARIANTS:
        verify_variant(v)
    print("All variants verified successfully!")
