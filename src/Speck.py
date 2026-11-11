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
from amaranth.back import verilog

def speck_round_fun(x, y, k, N, ALPHA, BETA):
	new_x = (x.rotate_right(ALPHA) + y)[:N] ^ k
	new_y = y.rotate_left(BETA) ^ new_x
	return new_x, new_y

def speck_inv_round_fun(x, y, k, N, ALPHA, BETA):
	new_y = (y ^ x).rotate_right(BETA)
	new_x = ((x ^ k) - new_y)[:N].rotate_left(ALPHA)
	return new_x, new_y

class ExpandKey(Elaboratable):
	def __init__(self, N=32, M=4, ALPHA=8, BETA=3, T=27):
		self.N = N
		self.M = M
		self.ALPHA = ALPHA
		self.BETA = BETA
		self.T = T

		self.key_in = Signal(N * M)
		self.key_out = Signal(N * T)

	def elaborate(self, platform):
		m = Module()

		N, M, T = self.N, self.M, self.T

		key = [Signal(N, name=f"key_{i}") for i in range(T + 1)]
		l   = [Signal(N, name=f"l_{i}")   for i in range(T + M)]

		m.d.comb += key[0].eq(self.key_in[0:N])

		for i in range(M-1):
			m.d.comb += l[i].eq(self.key_in[(i+1) * N : (i+2) * N])

		for i in range(T):
			nx, ny= speck_round_fun(l[i], key[i], Const(i, N), N, self.ALPHA, self.BETA)

			m.d.comb += [
				l[i+M-1].eq(nx),
				key[i + 1].eq(ny),
			]

		for i in range(T):
			m.d.comb += self.key_out[i*N: (i+1)*N].eq(key[i])

		return m

class Encrypt(Elaboratable):
	def __init__(self, N=32, M=4, ALPHA=8, BETA=3, T=27):
		self.N = N
		self.M = M
		self.ALPHA = ALPHA
		self.BETA = BETA
		self.T = T

		self.data_in = Signal(2*N)
		self.key = Signal(N*M)
		self.data_out = Signal(2*N)

	def elaborate(self, platform):
		m = Module()
		m.submodules.expand = expand = ExpandKey(self.N, self.M, self.ALPHA, self.BETA, self.T)

		m.d.comb += expand.key_in.eq(self.key)

		N, M, T = self.N, self.M, self.T

		x = [Signal(N, name=f"x_{i}") for i in range(T + 1)]
		y = [Signal(N, name=f"y_{i}") for i in range(T + 1)]

		m.d.comb += [
			x[0].eq(self.data_in[N:2 * N]),
			y[0].eq(self.data_in[0:N]),
		]
		for i in range(T):
			nx, ny = speck_round_fun(x[i], y[i], expand.key_out[i * N:(i + 1) * N],
										N, self.ALPHA, self.BETA)
			m.d.comb += [x[i + 1].eq(nx), y[i + 1].eq(ny)]

		m.d.comb += self.data_out.eq(Cat(y[T], x[T]))

		return m

class Decrypt(Elaboratable):
	def __init__(self, N=32, M=4, ALPHA=8, BETA=3, T=27):
		self.N = N
		self.M = M
		self.ALPHA = ALPHA
		self.BETA = BETA
		self.T = T

		self.data_in = Signal(2*N)
		self.key = Signal(N*M)
		self.data_out = Signal(2*N)

	def elaborate(self, platform):
		m = Module()
		m.submodules.expand = expand = ExpandKey(self.N, self.M, self.ALPHA, self.BETA, self.T)

		m.d.comb += expand.key_in.eq(self.key)

		N, M, T = self.N, self.M, self.T

		x = [Signal(N, name=f"x_{i}") for i in range(T + 1)]
		y = [Signal(N, name=f"y_{i}") for i in range(T + 1)]

		m.d.comb += [
			x[0].eq(self.data_in[N:2 * N]),
			y[0].eq(self.data_in[0:N]),
		]
		for j in range(T):
			rk = T - 1 - j
			nx, ny = speck_inv_round_fun(x[j], y[j], expand.key_out[rk * N:(rk + 1) * N],
											N, self.ALPHA, self.BETA)
			m.d.comb += [x[j + 1].eq(nx), y[j + 1].eq(ny)]

		m.d.comb += self.data_out.eq(Cat(y[T], x[T]))

		return m

# =====================================================================
# VERIFICATION
# =====================================================================
# The following code, including the test vectors and simulation setup,
# is strictly for testing and verifying the correctness of the crypto core.
# It is not required for hardware synthesis or integration into larger designs.
# =====================================================================

SPECK_VARIANTS = [
    {
        "name": "Speck32/64",
        "N": 16, "M": 4, "ALPHA": 7, "BETA": 2, "T": 22,
        "key": 0x1918111009080100,
        "pt":  0x6574694c,
        "ct":  0xa86842f2
    },
    {
        "name": "Speck48/72",
        "N": 24, "M": 3, "ALPHA": 8, "BETA": 3, "T": 22,
        "key": 0x1211100a0908020100,
        "pt":  0x20796c6c6172,
        "ct":  0xc049a5385adc
    },
    {
        "name": "Speck48/96",
        "N": 24, "M": 4, "ALPHA": 8, "BETA": 3, "T": 23,
        "key": 0x1a19181211100a0908020100,
        "pt":  0x6d2073696874,
        "ct":  0x735e10b6445d
    },
    {
        "name": "Speck64/96",
        "N": 32, "M": 3, "ALPHA": 8, "BETA": 3, "T": 26,
        "key": 0x131211100b0a090803020100,
        "pt":  0x74614620736e6165,
        "ct":  0x9f7952ec4175946c
    },
    {
        "name": "Speck64/128",
        "N": 32, "M": 4, "ALPHA": 8, "BETA": 3, "T": 27,
        "key": 0x1b1a1918131211100b0a090803020100,
        "pt":  0x3b7265747475432d,
        "ct":  0x8c6fa548454e028b
    },
    {
        "name": "Speck96/96",
        "N": 48, "M": 2, "ALPHA": 8, "BETA": 3, "T": 28,
        "key": 0x0d0c0b0a0908050403020100,
        "pt":  0x65776f68202c656761737520,
        "ct":  0x9e4d09ab717862bdde8f79aa
    },
    {
        "name": "Speck96/144",
        "N": 48, "M": 3, "ALPHA": 8, "BETA": 3, "T": 29,
        "key": 0x1514131211100d0c0b0a0908050403020100,
        "pt":  0x656d6974206e69202c726576,
        "ct":  0x2bf31072228a7ae440252ee6
    },
    {
        "name": "Speck128/128",
        "N": 64, "M": 2, "ALPHA": 8, "BETA": 3, "T": 32,
        "key": 0x0f0e0d0c0b0a09080706050403020100,
        "pt":  0x6c617669757165207469206564616d20,
        "ct":  0xa65d9851797832657860fedf5c570d18
    },
    {
        "name": "Speck128/192",
        "N": 64, "M": 3, "ALPHA": 8, "BETA": 3, "T": 33,
        "key": 0x17161514131211100f0e0d0c0b0a09080706050403020100,
        "pt":  0x726148206665696843206f7420746e65,
        "ct":  0x1be4cf3a13135566f9bc185de03c1886
    },
    {
        "name": "Speck128/256",
        "N": 64, "M": 4, "ALPHA": 8, "BETA": 3, "T": 34,
        "key": 0x1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100,
        "pt":  0x65736f6874206e49202e72656e6f6f70,
        "ct":  0x4109010405c0f53e4eeeb48d9c188f43
    }
]

def verify_variant(variant):
    """Dynamically creates a module for a variant and tests it."""
    N, M = variant["N"], variant["M"]
    A, B, T = variant["ALPHA"], variant["BETA"], variant["T"]

    enc = Encrypt(N=N, M=M, ALPHA=A, BETA=B, T=T)
    dec = Decrypt(N=N, M=M, ALPHA=A, BETA=B, T=T)

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

# if __name__ == "__main__":
#     # Verification
#     for v in SPECK_VARIANTS:
#         verify_variant(v)
#     print("All variants verified successfully!")
#
#     # generation of all variant (Encrypt + Decrypt)
#     for variant in SPECK_VARIANTS:
#         N = variant["N"]
#         M = variant["M"]
#         T = variant["T"]
#         ALPHA = variant["ALPHA"]
#         BETA = variant["BETA"]
#
#         # Calculate block size (x) and key size (y) for the filename
#         block_size = 2 * N
#         key_size = N * M
#
#         # Instantiate the Decrypt module
#         enc = Encrypt(N=N, M=M, T=T, ALPHA=ALPHA, BETA=BETA)
#         dec = Decrypt(N=N, M=M, T=T, ALPHA=ALPHA, BETA=BETA)
#         ports = [dec.data_in, dec.key, dec.data_out]
#
#         # Generate the filename: e.g., simon32_64_dec.v
#         filename1 = f"build/Speck/speck{block_size}_{key_size}_enc.v"
#         filename2 = f"build/Speck/speck{block_size}_{key_size}_dec.v"
#
#         # Convert and write to file
#         with open(filename1, "w") as f:
#             f.write(verilog.convert(enc, ports=ports))
#
#         with open(filename2, "w") as f:
#             f.write(verilog.convert(dec, ports=ports))
#
#         print(f"Generated {filename1}, {filename2} for {variant['name']}")
#
#     print("All 10 variant files emitted successfully!")
