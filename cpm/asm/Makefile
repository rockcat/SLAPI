# Makefile for CP/M assembly programs
# Uses zasm assembler to build .com files from .asm sources

# Assembler and flags
ASM = zasm
ASMFLAGS = -b --dotnames

# Source files
SOURCES = $(wildcard *.asm)

# Target files (.com)
TARGETS = $(SOURCES:.asm=.com)

# Default target: build all
all: $(TARGETS)

# Rule to build .com from .asm
%.com: %.asm
	$(ASM) $(ASMFLAGS) $< -o $@

# Clean build artifacts
clean:
	rm -f *.com *.lst *.sym

# Phony targets
.PHONY: all clean
