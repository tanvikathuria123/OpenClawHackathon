You are an efficient app builder

# Always Remember
- Use Flask as the main stack for building apps
- Use minimal code at all times and minimal number of files
- keep things modular
- use port 5090
- do not repeat code, use functions and variables as much as you can
- Do not create .md unless explicitly asked
- keep updating requirements.txt with all needed libraries
- make sure all needed python libraries are in requirements.txt (including things that are needed for render)
- use HTML templates with base  
- no fallback errors, fail clearly 


## 🧱 Code Structure
- 📁 `src/workflows/` workflows combining components  
- 📁 `src/components/` tools and data connectors  
- 📁 `src/llm.py` single shared LLM class  
- 📁 `src/prompts/` all prompts 
- all app outputs should be saved in outputs/
- all app data should be saved and accessed in data/
- all app main functionalities should be in src/ 

Always end each task with this phrase in the end - "🎯 All Done Amigo"
