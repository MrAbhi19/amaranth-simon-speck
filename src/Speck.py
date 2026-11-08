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
