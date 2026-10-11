#!/usr/bin/env python3
"""
Coding-puppy Local ai code analyzer/boiler-plate generator
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
import readline  # Enables history and editing in input()

load_dotenv()

model = os.getenv("OLLAMA_MODEL")

class CodeAnalyzerAgent:
    """Agent for analyzing code files with Ollama"""
    
    def __init__(self, model: str = model):
        self.model = model
        self.current_dir = Path.cwd()
        self.history = []
        self._verify_ollama()

    def _verify_ollama(self):
        """Verify Ollama is running and model is available"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                print("❌ Error: Ollama doesn't appear to be running")
                print("   Please start Ollama and try again")
                sys.exit(1)

            if self.model not in result.stdout:
                print(f"⚠️  Model '{self.model}' not found")
                print(f"   Available models:\n{result.stdout}")
                sys.exit(1)

            print(f"✓ Ollama is running with '{self.model}' available\n")
        except FileNotFoundError:
            print("❌ Error: Ollama CLI not found. Please install Ollama.")
            sys.exit(1)

    def search_file(self, filename: str) -> Optional[Path]:
        """
        Search for a file in current directory and child directories only.
        """
        print(f"\n🔍 Searching for '{filename}'...")

        # Search current directory and all subdirectories
        for root, dirs, files in os.walk(self.current_dir):
            if filename in files:
                found_path = Path(root) / filename
                print(f"✓ Found: {found_path}")
                return found_path

        print(f"❌ Not found in {self.current_dir} or its subdirectories")
        return None

    def read_file(self, filepath: Path, start_line: Optional[int] = None, 
                  end_line: Optional[int] = None) -> Optional[str]:
        """
        Read file content. If lines specified, return only that snippet.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            total_lines = len(lines)

            if start_line is not None and end_line is not None:
                # Validate line numbers
                if start_line < 1 or end_line > total_lines or start_line > end_line:
                    print(f"❌ Invalid line range. File has {total_lines} lines")
                    return None

                # Extract snippet (convert to 0-indexed)
                snippet = ''.join(lines[start_line - 1:end_line])
                print(f"✓ Read lines {start_line}-{end_line} from {filepath.name}")
                return snippet
            else:
                # Read entire file
                content = ''.join(lines)
                print(f"✓ Read full file ({total_lines} lines) from {filepath.name}")
                return content

        except FileNotFoundError:
            print(f"❌ File not found: {filepath}")
            return None
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return None

    def parse_analyze_command(self, command: str) -> Tuple[Optional[str], Optional[int], 
                                                            Optional[int], Optional[str]]:
        """
        Parse Analyze command syntax.
        Format: "Analyze: filepath:start-end, instructions"
        or: "Analyze: filepath, instructions"
        """
        # Check if command starts with Analyze:
        if not command.strip().startswith("Analyze:"):
            return None, None, None, None

        # Remove "Analyze:" prefix
        command = command.strip()[8:].strip()

        # Split by comma to separate file spec from instructions
        parts = command.split(',', 1)
        if len(parts) < 2:
            print("❌ Invalid format. Use: Analyze: <file>[:<start>-<end>], <instructions>")
            return None, None, None, None

        file_spec = parts[0].strip()
        instructions = parts[1].strip()

        # Parse file specification
        if ':' in file_spec:
            filepath_str, line_range = file_spec.rsplit(':', 1)
            match = re.match(r'(\d+)-(\d+)', line_range)
            if not match:
                print("❌ Invalid line range format. Use: filename:start-end")
                return None, None, None, None
            start_line = int(match.group(1))
            end_line = int(match.group(2))
        else:
            filepath_str = file_spec
            start_line = None
            end_line = None

        return filepath_str, start_line, end_line, instructions

    def parse_suggest_command(self, command: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse Suggest command syntax.
        Format: "Suggest: filepath, suggestion_instructions"
        """
        if not command.strip().startswith("Suggest:"):
            return None, None

        command = command.strip()[8:].strip()
        parts = command.split(',', 1)

        if len(parts) < 2:
            print("❌ Invalid format. Use: Suggest: <file>, <instructions>")
            return None, None

        filepath_str = parts[0].strip()
        instructions = parts[1].strip()

        return filepath_str, instructions

    def parse_generate_command(self, command: str) -> Tuple[Optional[str], Optional[str], 
                                                         Optional[list], Optional[str]]:
        """
        Parse Generate command syntax (free-form).
        Format: "Generate: filename.ext, description with (field1: type, field2, ...)"
    
        Returns: (filename, classname, fields_list, customization)
        """
        if not command.strip().startswith("Generate:"):
            return None, None, None, None

        command = command.strip()[9:].strip()
    
        # Extract filename
        parts = command.split(',', 1)
        if len(parts) < 1:
            print("❌ Invalid format. Use: Generate: filename.ext, description with (fields)")
            return None, None, None, None

        filename = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""

        # Derive class name from filename (user.java -> User)
        classname = Path(filename).stem
        classname = classname[0].upper() + classname[1:] if classname else "Generated"
        # Extract fields from parentheses
        fields_list = []
        import re
        fields_match = re.search(r'\(([^)]+)\)', rest)
    
        if fields_match:
            fields_str = fields_match.group(1)
            field_entries = [f.strip() for f in fields_str.split(',')]
        
            for entry in field_entries:
                if ':' in entry:
                    # Has explicit type
                    field_name, field_type = entry.split(':', 1)
                    fields_list.append({
                        'name': field_name.strip(),
                        'type': field_type.strip()
                    })
                else:
                    # Default to String
                    fields_list.append({
                        'name': entry.strip(),
                        'type': 'String'
                    })
    
        # Extract customization (e.g., "include getters and constructor only")
        customization = rest.replace(fields_match.group(0), "").strip() if fields_match else rest
    
        if not fields_list:
            print("❌ No fields found. Format: Generate: filename.ext, description with (field1: type, field2)")
            return None, None, None, None

        return filename, classname, fields_list, customization

    def detect_language(self, filepath: str) -> str:
        """Detect language from file extension"""
        extension = Path(filepath).suffix.lower()
        language_map = {
            '.java': 'Java',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript/React',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript/React',
            '.py': 'Python',
            '.rs': 'Rust',
            '.go': 'Go',
            '.cpp': 'C++',
            '.cs': 'C#',
        }
        return language_map.get(extension, 'Unknown')


    def normalize_types(self, field_type: str, language: str) -> str:
        """
        Normalize field types to language-appropriate equivalents.
        Simple type mapping for common types.
        """
        field_type = field_type.strip().lower()

        type_map = {
            'int': {'Java': 'int', 'Python': 'int', 'TypeScript': 'number', 'JavaScript': 'number', 'Go': 'int', 'Rust': 'i32'},
            'string': {'Java': 'String', 'Python': 'str', 'TypeScript': 'string', 'JavaScript': 'string', 'Go': 'string', 'Rust': 'String'},
            'bool': {'Java': 'boolean', 'Python': 'bool', 'TypeScript': 'boolean', 'JavaScript': 'boolean', 'Go': 'bool', 'Rust': 'bool'},
            'float': {'Java': 'float', 'Python': 'float', 'TypeScript': 'number', 'JavaScript': 'number', 'Go': 'float64', 'Rust': 'f32'},
            'double': {'Java': 'double', 'Python': 'float', 'TypeScript': 'number', 'JavaScript': 'number', 'Go': 'float64', 'Rust': 'f64'},
            'boolean': {'Java': 'boolean', 'Python': 'bool', 'TypeScript': 'boolean', 'JavaScript': 'boolean', 'Go': 'bool', 'Rust': 'bool'},
        }

        if field_type in type_map:
            return type_map[field_type].get(language, field_type)

        # If not in map, return as-is (could be custom types)
        return field_type[0].upper() + field_type[1:] if field_type else 'String'


    def build_generate_prompt(self, classname: str, language: str, fields: list, 
                             customization: str) -> str:
        """
        Build a clear prompt for the LLM to generate boilerplate.
        """
        fields_str = "\n".join([f"- {f['name']}: {f['type']}" for f in fields])

        # Default includes
        includes = "field declarations and getters/setters"
        if customization:
            includes = customization

        prompt = f"""Generate: {classname}.{Path(classname).suffix if classname else language.lower()}

    Language: {language}
    Class: {classname}

    Fields:
    {fields_str}

    Include: {includes}

    Generate clean, minimal boilerplate code. No comments or extra documentation."""

        return prompt

    def strip_markdown_fences(self, code: str) -> str:
        """Remove markdown code fences from generated code"""
        import re
        # Remove opening fence (e.g., ```java, ```python, etc.)
        code = re.sub(r'^```[a-zA-Z0-9]*\n', '', code)
        # Remove closing fence
        code = re.sub(r'\n```$', '', code)
        return code.strip()

    def generate_code(self, filename: str, classname: str, language: str, 
                     fields: list, customization: str) -> Optional[str]:
        """
        Send generation request to Ollama
        """
        prompt = self.build_generate_prompt(classname, language, fields, customization)

        print("\n⏳ Generating boilerplate with Ollama...\n")
        print("-" * 60)

        try:
            result = subprocess.run(
                ["ollama", "run", self.model, prompt],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                generated_code = result.stdout.strip()
                return generated_code
            else:
                print(f"❌ Ollama error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("❌ Generation timed out")
            return None
        except Exception as e:
            print(f"❌ Error during generation: {e}")
            return None


    def handle_generate_command(self, filename: str, classname: str, 
                               fields: list, customization: str):
        """
        Handle the full generate workflow: generate → preview → confirm → save
        """
        language = self.detect_language(filename)

        if language == 'Unknown':
            print(f"❌ Unknown file extension. Supported: .java, .ts, .tsx, .js, .jsx, .py, .rs, .go, .cpp, .cs")
            return

        # Normalize types to language-appropriate equivalents
        for field in fields:
            field['type'] = self.normalize_types(field['type'], language)

        print(f"\n📝 Generating {classname} boilerplate ({language})...")

        # Generate code
        generated_code = self.generate_code(filename, classname, language, fields, customization)

        if not generated_code:
            return
        # Strip markdown fences before processing
        generated_code = self.strip_markdown_fences(generated_code)
        
        # Display preview
        print("\n" + "=" * 60)
        print(f"Preview: {filename}\n")
        print(generated_code)
        print("=" * 60)

        # Confirm generation
        confirm = input("\n✓ Generate this file? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("❌ Generation cancelled")
            return

        # Ask for directory
        target_dir = input("📁 Enter directory to save (relative or absolute path): ").strip()
        if not target_dir:
            target_dir = str(self.current_dir)

        target_path = Path(target_dir).resolve() / filename

        # Check if file exists
        if target_path.exists():
            overwrite = input(f"⚠️  File already exists: {target_path}\nOverwrite? (yes/no): ").strip().lower()
            if overwrite not in ['yes', 'y']:
                print("❌ Save cancelled")
                return

        # Create directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(generated_code)
            print(f"✓ File created: {target_path}")
        except Exception as e:
            print(f"❌ Error writing file: {e}")

    def analyze_code(self, filepath: Path, content: str, 
                    start_line: Optional[int], end_line: Optional[int],
                    instructions: str) -> str:
        """
        Send code to Ollama for analysis
        """
        # Build context message
        if start_line and end_line:
            context = f"Analyzing lines {start_line}-{end_line} of {filepath.name}:\n\n"
        else:
            context = f"Analyzing full file {filepath.name}:\n\n"

        context += f"```\n{content}\n```\n\n"
        context += f"Analysis instructions: {instructions}"

        prompt = f"Analyze: {filepath.name}:{start_line}-{end_line if start_line else 'full'}, {instructions}\n\n{context}"

        print("\n⏳ Analyzing code with Ollama...\n")
        print("-" * 60)

        try:
            result = subprocess.run(
                ["ollama", "run", self.model, prompt],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for long analyses
            )

            if result.returncode == 0:
                analysis = result.stdout.strip()
                self.history.append({
                    'file': str(filepath),
                    'lines': f"{start_line}-{end_line}" if start_line else "full",
                    'instructions': instructions,
                    'analysis': analysis
                })
                return analysis
            else:
                print(f"❌ Ollama error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("❌ Analysis timed out")
            return None
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            return None

    def display_help(self):
        """Display help information"""
        help_text = """
╔═══════════════════════════════════════════════════════════════╗
║           Coding-puppy - Command Help                ║
╚═══════════════════════════════════════════════════════════════╝

MAIN COMMANDS:
  Analyze: <file>[:<start>-<end>], <instructions>
    Analyze a code file with specific instructions
    
    Examples:
      • Analyze: component.rs:11-20, Search for bugs and typos.
      • Analyze: main.py, Review for performance issues.
      • Analyze: helper.js, Check for security vulnerabilities.

  search <filename>
    Search for a file in current directory and subdirectories
    
    Example:
      • search component.rs
  Generate: <filename>, description with (<field1>: <type>, <field2>, ...)
    Generate boilerplate code with specified fields
    
    Examples:
      • Generate: user.java, with (id: int, firstname, lastname, phonenumber)
      • Generate: config.py, with (host: string, port: int, debug)
      • Generate: Person.ts, class with (name, age: number, email) include constructor

  help
    Show this help message

  history
    Show previous analyses

  cd <directory>
    Change working directory

  pwd
    Show current working directory

  exit / quit
    Exit the analyzer

═══════════════════════════════════════════════════════════════

ANALYSIS INSTRUCTIONS EXAMPLES:
  • "Search for bugs and typos."
  • "Check for security vulnerabilities."
  • "Review code style and best practices."
  • "Identify performance bottlenecks."
  • "Check for memory leaks or resource issues."
  • "Review error handling."

═══════════════════════════════════════════════════════════════
        """
        print(help_text)

    def show_history(self):
        """Display analysis history"""
        if not self.history:
            print("\n📝 No analysis history yet")
            return

        print("\n📜 Analysis History:")
        print("=" * 60)
        for i, item in enumerate(self.history, 1):
            print(f"\n{i}. File: {item['file']}")
            print(f"   Lines: {item['lines']}")
            print(f"   Instructions: {item['instructions']}")
            print(f"   Analysis:\n   {'-' * 56}")
            # Show first 200 chars of analysis
            preview = item['analysis'][:200].replace('\n', '\n   ')
            print(f"   {preview}...")
            print(f"   {'-' * 56}")

    def run_interactive(self):
        """Run the interactive prompt loop"""
        print("\n" + "=" * 60)
        print("🤖 Coding-puppy Analyzer - Interactive Mode")
        print("=" * 60)
        print(f"Model: {self.model}")
        print(f"Working directory: {self.current_dir}")
        print("\nType 'help' for commands or start analyzing!\n")

        while True:
            try:
                user_input = input(">>> ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() == "help":
                    self.display_help()
                    continue

                elif user_input.lower() == "history":
                    self.show_history()
                    continue

                elif user_input.lower() in ["exit", "quit"]:
                    print("\n👋 Goodbye!")
                    break

                elif user_input.lower() == "pwd":
                    print(f"📁 Current directory: {self.current_dir}")
                    continue

                elif user_input.lower().startswith("cd "):
                    new_dir = user_input[3:].strip()
                    try:
                        self.current_dir = Path(new_dir).resolve()
                        print(f"✓ Changed to: {self.current_dir}")
                    except Exception as e:
                        print(f"❌ Error: {e}")
                    continue

                elif user_input.lower().startswith("search "):
                    filename = user_input[7:].strip()
                    found = self.search_file(filename)
                    if found:
                        print(f"📂 Full path: {found.absolute()}")
                    continue

                # Handle Analyze command
                elif user_input.startswith("Analyze:"):
                    filepath_str, start_line, end_line, instructions = \
                        self.parse_analyze_command(user_input)

                    if filepath_str is None:
                        continue

                    # Search for file
                    filepath = self.search_file(filepath_str)
                    if filepath is None:
                        continue

                    # Read file
                    content = self.read_file(filepath, start_line, end_line)
                    if content is None:
                        continue

                    # Analyze
                    analysis = self.analyze_code(filepath, content, 
                                                start_line, end_line, instructions)
                    if analysis:
                        print(analysis)
                        print("-" * 60)
                    continue
                
                # Handle Suggest command
                elif user_input.startswith("Suggest:"):
                    filepath_str, instructions = self.parse_suggest_command(user_input)
                    # Similar flow to Analyze but with different prompt format

                 # Handle Generate command
                elif user_input.startswith("Generate:"):
                    filename, classname, fields, customization = \
                        self.parse_generate_command(user_input)

                    if filename is None:
                        continue

                    self.handle_generate_command(filename, classname, fields, customization)
                    continue

                else:
                    print("❌ Unknown command. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main entry point"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║      Coding-puppy Ai code analyzer/boiler-plate generator      ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)

    agent = CodeAnalyzerAgent(model=model)
    agent.run_interactive()


if __name__ == "__main__":
    main()

