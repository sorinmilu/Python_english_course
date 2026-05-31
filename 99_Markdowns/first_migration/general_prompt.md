You are acting as an elite academic copyeditor and systems programmer. Your task is to create a new content tree called 01_REDUCED_CONTENT, based on all the content in 00_CONTENT and a strict "Decompression and Pruning" strategy. 

## Description of the source material

The directories in 00_CONTENT hold a latex file called "content.tex" and another one called "references.bib". At the top of each file there is the current heading (\chapter, section, etc). All the directories are listed in 03_SCRIPTS/main_project.json, in the key "inspected_folders".

## Description of the target material 

The target material should create the same folder structure in the 01_REDUCED_CONTENT. The subdirectories should be the same if they are copied or rewritten and different if the sections/subsections names are changed. 

At the end, write a 03_SCRIPTS/reduced_project.json that contains the same keys as 03_SCRIPTS/main_project with the new structure in the "inspected_folders"


Apply the following three core architectural directives to the text:

Follow the following files:

99_Markdowns\first_migration\chapter_2_mini-prompts.md
99_Markdowns\first_migration\chapter_3_mini-prompts.md
99_Markdowns\first_migration\chapter_4_mini-prompts.md
99_Markdowns\first_migration\chapter_5_mini-prompts.md
99_Markdowns\first_migration\chapter_6_mini-prompts.md
99_Markdowns\first_migration\chapter_7_mini-prompts.md
99_Markdowns\first_migration\chapter_8_mini-prompts.md
99_Markdowns\first_migration\chapter_9_mini-prompts.md

Each file corresponds to a chapter in the 00_CONTENT. Inside each file you will find instructions at section level. There are two kind of instructions:

### Skipping
The skipping implies simply not including the correponsing directories from 00_CONTENT to 01_REDUCED_CONTENT

## 3. Systems-Engineering Condensations

Summarize and condense the sections specified in the chapter prompts

### Execution Constraints:
* Maintain flawless LaTeX syntax. Do not break macros, math environments, or file compilation structures.
* Do not truncate code blocks or use placeholder comments like "% [rest of code here]". Output the fully rewritten, compile-ready LaTeX text.

Confirm you understand this framework and await the input data.

