# Amaranth Speck Core

This repository contains fully unrolled `Speck` and `Simon` block cipher implementations written in the `Amaranth hardware description language`. Both cores are fully parameterized, allowing you to generate any of the 10 standard variants for either cipher.

## Architecture Notes

* **Single-Cycle Latency:** These implementations are completely combinational (0 clock cycles). They are optimized for minimum single-cycle latency. Because the unrolled rounds create a long combinatorial critical path, maximum clock frequencies will be lower compared to pipelined designs.
* **Independent Modules:** The `Encrypt` and `Decrypt` modules are strictly decoupled and can be used independently as drop-in components. Both modules internally instantiate their own `ExpandKey` logic. If your design requires both encryption and decryption, your synthesis tool may deduplicate the identical key expansion logic, though this behavior depends on your specific toolchain and synthesis constraints.

## Verification

The repository includes a native Amaranth test framework that dynamically tests both the Encrypt and Decrypt modules. It verifies the encryption and full round-trip decryption for all 10 standard Speck configurations and all 10 standard Simon configurations directly against the official NSA test vectors.

Additionally, the Amaranth-generated Verilog for all Speck variants has been validated using equivalence testing (via Yosys-eqy) against a proven reference Verilog implementation. (Note: Equivalence testing against a golden Verilog reference is currently only available for the Speck core, as a Verilog reference model for Simon has not yet been implemented). I also authored the Speck reference model, which was verified against the same official NSA test vectors. You can view the golden reference here:
[OnyxRTL/CipherCore/tree/main/Speck](https://github.com/OnyxRTL/CipherCore/tree/main/SPECK)

## Usage

> **Note:** The `if __name__ == "__main__":` block at the bottom of both `Speck.py` and `Simon.py` is **commented out by default**. Uncomment the relevant part for the workflow you want (verification, generate-all, or generate-one) before running.

### Verification

Uncomment the `if __name__ == "__main__":` line **and** the verification loop, then run the file directly:

```python
if __name__ == "__main__":
    # Verification
    for v in SPECK_VARIANTS:
    # or
    # for v in SIMON_VARIANTS: (for Simon)
        verify_variant(v)
    print("All variants verified successfully!")
```

Then run:

```bash
python Speck.py
# or
python Simon.py
```

You will see output like `Verified Speck32/64`, `Verified Speck48/72`, … for each variant, or an assertion failure pointing at the failing variant if any test vector mismatches.

### Generating all 10 variants (Encrypt and Decrypt)

Uncomment the **entire** `if __name__ == "__main__":` block (verification is **optional**). Make sure a `build/Simon` or `build/Speck` directory exists next to the script — the generator assumes it is already there and will fail loudly if it is missing.

```python
if __name__ == "__main__":
    # Verification
    for v in SPECK_VARIANTS:
        verify_variant(v)
    print("All variants verified successfully!")

    # Generation of all variants (Encrypt + Decrypt)
    for variant in SIMON_VARIANTS:
        N = variant["N"]
        M = variant["M"]
        T = variant["T"]
        J = variant["J"]

        # Calculate block size (x) and key size (y) for the filename
        block_size = 2 * N
        key_size = N * M

        # Instantiate the Decrypt module
        enc = Encrypt(N=N, M=M, T=T, J=J)
        dec = Decrypt(N=N, M=M, T=T, J=J)
        ports = [dec.data_in, dec.key, dec.data_out]

        # Generate the filename: e.g., simon32_64_dec.v
        filename1 = f"build/Simon/simon{block_size}_{key_size}_enc.v"
        filename2 = f"build/Simon/simon{block_size}_{key_size}_dec.v"

        # Convert and write to file
        with open(filename1, "w") as f:
            f.write(verilog.convert(enc, ports=ports))

        with open(filename2, "w") as f:
            f.write(verilog.convert(dec, ports=ports))

        print(f"Generated {filename1}, {filename2} for {variant['name']}")

    print("All 10 variant files emitted successfully!")
```

Run:

```bash
python Speck.py
```

This emits 20 files into `build/Simon` or `build/Speck` — one `_enc.v` and one `_dec.v` per variant.

### Generating only 1 design

If you only need a single variant, you don't need `SPECK_VARIANTS` at all — instantiate `Encrypt`/`Decrypt` directly with that variant's parameters. For example, to emit only **Speck64/128** (`N=32, M=4, T=27`):

```python
if __name__ == "__main__":
    enc = Encrypt(N=32, M=4, ALPHA=8, BETA=3, T=27)
    dec = Decrypt(N=32, M=4, ALPHA=8, BETA=3, T=27)

    with open("speck64_128_enc.v", "w") as f:
        f.write(verilog.convert(enc, ports=[enc.data_in, enc.key, enc.data_out]))
    with open("speck64_128_dec.v", "w") as f:
        f.write(verilog.convert(dec, ports=[dec.data_in, dec.key, dec.data_out]))

    print("Generated build/speck64_128_enc.v and build/speck64_128_dec.v")
```

Swap the `N`/`M`/`T`/`ALPHA`/`BETA` values for whichever variant you want — see the `SPECK_VARIANTS` table at the top of `Speck.py` for the exact parameters of each of the 10 standard configurations.

Run:

```bash
python Speck.py
```

## Roadmap

Active work is ongoing to expand thes core's capabilities. Upcoming additions include:
- **Fully Pipelined Architecture:** Expanding the design to include a pipelined variant optimized for high throughput and higher clock frequencies.
- **Serial Architecture:** Adding a multi-cycle, iterative architecture for strict area-constrained applications.

