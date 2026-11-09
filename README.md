# Amaranth Speck Core

This repository contains a fully unrolled Speck core implementation written in the Amaranth hardware description language. It is fully parameterized, allowing you to generate any of the 10 standard Speck variants.

## Architecture Notes

* **Single-Cycle Latency:** This implementation is completely combinational (0 clock cycles). It is optimized for minimum single-cycle latency. Because the unrolled rounds create a long combinatorial critical path, maximum clock frequencies will be lower compared to pipelined designs.
* **Independent Modules:** The `Encrypt` and `Decrypt` modules are strictly decoupled and can be used independently as drop-in components. Both modules internally instantiate their own `ExpandKey` logic. If your design requires both encryption and decryption, your synthesis tool may deduplicate the identical key expansion logic, though this behavior depends on your specific toolchain and synthesis constraints.

## Verification

The core includes a native Amaranth test framework that dynamically tests both the `Encrypt` and `Decrypt` modules. It verifies the encryption and full round-trip decryption for all 10 standard Speck configurations directly against the official NSA test vectors.

Additionally, the Amaranth-generated Verilog for all variants has been validated using equivalence testing (via Yosys-eqy) against a proven reference Verilog implementation. I also authored the reference model, which was verified against the same official NSA test vectors. You can view the golden reference here:
[OnyxRTL/CipherCore/tree/main/Speck](https://github.com/OnyxRTL/CipherCore/tree/main/SPECK)

## Roadmap

Active work is ongoing to expand this core's capabilities. Upcoming additions include:
- **Fully Pipelined Architecture:** Expanding the design to include a pipelined variant optimized for high throughput and higher clock frequencies.
- **Serial Architecture:** Adding a multi-cycle, iterative architecture for strict area-constrained applications.
