# RRCommon

A community-driven repository of reusable SystemVerilog IP modules generated with AI assistance.

#Note: This is considered pre-release - no modules have yet been fully verified. We welcome contributions!

## Purpose

RRCommon serves two main purposes:

1. **Reusable IP Library**: A collection of AI-generated SystemVerilog IP modules that FPGA engineers can use in their projects.
2. **AI Agent Development Template**: A starter repository with predefined rules and workflows to help engineers create their own custom modules using AI assistance.

## Repository Structure

```
rrcommon/
├── <module_name>/             # Directory for each module
│   ├── <module_name>.sv       # SystemVerilog RTL module
│   ├── test_<module_name>.py  # Cocotb testbench
│   ├── Makefile               # Build configuration
│   ├── README.md              # Module documentation
│   └── changes.txt            # Debug/change history
├── README.md                  # This file
└── .cursor/rules              # AI development rules
```

## Getting Started

### Using Existing Modules

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/rrcommon.git
   ```

2. Navigate to the module directory you're interested in
3. Review the module's README.md for documentation on usage
4. Copy the module files to your project or include this repository as a submodule

### Testing Modules

Most modules use [cocotb](https://github.com/cocotb/cocotb) for verification. To run tests:

1. Install cocotb:
   ```bash
   pip install cocotb
   ```

2. Navigate to a module directory
3. Run tests:
   ```bash
   make clean && make
   ```

4. View waveforms (requires GTKWave):
   ```bash
   gtkwave sim_build/<module_name>.fst
   ```

### Developing New Modules

This repository includes AI agent rules for developing new modules:

1. Use the repository with an AI coding assistant that supports rule files (e.g., Cursor)
2. Follow the guidelines in the rule files located in `.cursor/rules/`
3. Request the AI to create a new module by providing a clear description

## Contributing

Contributions are welcome! You can:

1. **Fix bugs** in existing modules
2. **Add new modules** following the repository structure
3. **Update core rules** to improve AI-assisted development
4. **Share your own rulesets** for specialized module development

For contributions:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request with a clear description of your changes

## Rule Sets

The repository contains several rule sets for AI-assisted development:

- `codingstandards.mdc`: SystemVerilog coding standards and best practices
- `gencocotb.mdc`: Guidelines for generating cocotb testbenches
- `autodebug.mdc`: Automated debugging workflows for SystemVerilog modules
- `newmodule.mdc`: Process for creating new module directories and files

To use these rules, you need an AI coding assistant that supports custom rule files.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
