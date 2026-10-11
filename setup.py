import os
import subprocess
from pathlib import Path

def main():
    env_file = Path(".env")
    modelfile = Path("Modelfile")
    
    # Step 1: Check if .env exists
    if env_file.exists():
        overwrite = input(".env already exists. Overwrite? (y/n): ").lower()
        if overwrite != "y":
            print("Cancelled.")
            return
    
    # Step 2: Check if Modelfile exists
    if not modelfile.exists():
        print("ERROR: Modelfile not found in current directory")
        return
    
    # Step 3: Ask for base model
    base_model = input("What base model do you want to use? ").strip()
    
    # Step 4: Read and modify Modelfile
    try:
        lines = modelfile.read_text().splitlines(keepends=True)
        
        # Find and replace the FROM line
        modified = False
        for i, line in enumerate(lines):
            if line.strip().upper().startswith("FROM "):
                lines[i] = f"FROM {base_model}\n"
                modified = True
                break
        
        if not modified:
            print("ERROR: No FROM line found in Modelfile")
            return
        
        # Write modified Modelfile back
        modelfile.write_text("".join(lines))
        print(f"✓ Modelfile updated with base model '{base_model}'")
        
    except Exception as e:
        print(f"ERROR: Failed to modify Modelfile: {e}")
        return
    
    # Step 5: Ask for custom model name
    model_name = input("What name do you want for this model? ").strip()
    
    # Step 6: Run ollama create command
    print(f"Creating model '{model_name}'...")
    try:
        result = subprocess.run(
            ["ollama", "create", model_name, "-f", "Modelfile"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Model '{model_name}' created successfully")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create model")
        print(f"Details: {e.stderr}")
        return
    except FileNotFoundError:
        print("ERROR: ollama command not found. Is ollama installed?")
        return
    
    # Step 7: Ask for languages
    #print("\nSelect languages (comma-separated): rust, javascript, java, go")
    #languages = input("Languages: ").strip()
    
    # Step 8: Create .env file
    env_content = f"""OLLAMA_MODEL={model_name}
    """
    
    env_file.write_text(env_content)
    print(f"✓ .env created successfully")

if __name__ == "__main__":
    main()
