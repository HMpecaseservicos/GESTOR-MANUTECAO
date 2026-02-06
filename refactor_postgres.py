#!/usr/bin/env python3
"""
Script to automatically refactor app.py from SQLite+PostgreSQL to PostgreSQL-only.
This removes all if Config.IS_POSTGRES: ... else: sqlite3... patterns.
"""

import re
import sys

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    blocks_fixed = 0
    
    # Pattern 1: Simple if/else connection blocks
    # Matches blocks like:
    # if Config.IS_POSTGRES:
    #     import psycopg2
    #     conn = psycopg2.connect(Config.DATABASE_URL)
    # else:
    #     conn = sqlite3.connect(DATABASE)
    
    # First, let's find and fix simple inline ternary expressions
    # Pattern: 'PostgreSQL' if Config.IS_POSTGRES else 'SQLite'
    pattern_ternary = r"'PostgreSQL' if Config\.IS_POSTGRES else 'SQLite'"
    content, n = re.subn(pattern_ternary, "'PostgreSQL'", content)
    blocks_fixed += n
    
    # Pattern: 'produção' if Config.IS_POSTGRES else 'desenvolvimento'
    pattern_ternary2 = r"'produção' if Config\.IS_POSTGRES else 'desenvolvimento'"
    content, n = re.subn(pattern_ternary2, "'produção'", content)
    blocks_fixed += n
    
    # Pattern: 'true' if Config.IS_POSTGRES else '1'
    pattern_ternary3 = r"'true' if Config\.IS_POSTGRES else '1'"
    content, n = re.subn(pattern_ternary3, "'true'", content)
    blocks_fixed += n
    
    # Pattern: ativo_val = 'true' if Config.IS_POSTGRES else '1'
    pattern_ativo = r"ativo_val = 'true' if Config\.IS_POSTGRES else '1'"
    content, n = re.subn(pattern_ativo, "ativo_val = 'true'", content)
    blocks_fixed += n
    
    # Pattern for simple one-line if/else queries
    # if Config.IS_POSTGRES:
    #     cursor.execute('... %s ...', (param,))
    # else:
    #     cursor.execute('... ? ...', (param,))
    
    # Complex pattern for if/else blocks
    # This is a more sophisticated approach using a state machine
    
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check for if Config.IS_POSTGRES: pattern
        if re.match(r'^(\s*)if Config\.IS_POSTGRES:', line):
            indent_match = re.match(r'^(\s*)', line)
            base_indent = indent_match.group(1) if indent_match else ''
            
            # Find the else: and collect the if-branch
            j = i + 1
            if_branch = []
            else_found = False
            else_line_idx = -1
            
            # Calculate expected indent for block contents
            if j < len(lines):
                content_match = re.match(r'^(\s*)', lines[j])
                content_indent = content_match.group(1) if content_match else base_indent + '    '
            else:
                content_indent = base_indent + '    '
            
            # Collect if-branch lines until we find else:
            while j < len(lines):
                current_line = lines[j]
                current_stripped = current_line.strip()
                
                # Check for else: at the same indent level as the if
                if current_stripped == 'else:' and current_line.startswith(base_indent) and len(re.match(r'^(\s*)', current_line).group(1)) == len(base_indent):
                    else_found = True
                    else_line_idx = j
                    break
                
                # Check if we've exited the block (line at same or lesser indent that's not empty)
                if current_stripped and not current_line.startswith(content_indent) and not current_stripped.startswith('#'):
                    # Back at base indent or less - no else found
                    break
                
                if_branch.append(current_line)
                j += 1
            
            if else_found:
                # Now skip the else branch
                k = else_line_idx + 1
                while k < len(lines):
                    current_line = lines[k]
                    current_stripped = current_line.strip()
                    
                    # Check if we've exited the else block
                    if current_stripped and not current_line.startswith(content_indent) and not current_stripped.startswith('#'):
                        break
                    k += 1
                
                # Add the if-branch lines (without the 'if Config.IS_POSTGRES:' and dedented)
                # But first, clean up the if-branch:
                # - Remove redundant 'import psycopg2' and 'from psycopg2.extras import RealDictCursor'
                #   since they're now imported at the top level
                for branch_line in if_branch:
                    cleaned_line = branch_line
                    
                    # Skip redundant local imports (now global)
                    if 'import psycopg2' in branch_line and 'from' not in branch_line:
                        # Check if this is a standalone import line
                        if branch_line.strip() == 'import psycopg2':
                            continue
                    if 'from psycopg2.extras import RealDictCursor' in branch_line:
                        if branch_line.strip() == 'from psycopg2.extras import RealDictCursor':
                            continue
                    
                    # Dedent by one level (remove 4 spaces from the beginning)
                    if cleaned_line.startswith(base_indent + '    '):
                        cleaned_line = base_indent + cleaned_line[len(base_indent) + 4:]
                    
                    new_lines.append(cleaned_line)
                
                blocks_fixed += 1
                i = k
                continue
            else:
                # No else found - this might be a standalone if block
                # Check if it's like: if Config.IS_POSTGRES and ...
                if 'and' in stripped:
                    # Keep the line but remove the Config.IS_POSTGRES check
                    # e.g., "if Config.IS_POSTGRES and Config.DATABASE_URL:" -> "if Config.DATABASE_URL:"
                    new_line = line.replace('Config.IS_POSTGRES and ', '')
                    new_lines.append(new_line)
                    blocks_fixed += 1
                    i += 1
                    continue
                else:
                    # Standalone if with just IS_POSTGRES - always execute the block
                    # Skip the if line and dedent the block
                    for branch_line in if_branch:
                        cleaned_line = branch_line
                        
                        # Skip redundant local imports
                        if branch_line.strip() == 'import psycopg2':
                            continue
                        if branch_line.strip() == 'from psycopg2.extras import RealDictCursor':
                            continue
                        
                        # Dedent by one level
                        if cleaned_line.startswith(base_indent + '    '):
                            cleaned_line = base_indent + cleaned_line[len(base_indent) + 4:]
                        
                        new_lines.append(cleaned_line)
                    
                    blocks_fixed += 1
                    i = j
                    continue
        
        new_lines.append(line)
        i += 1
    
    content = '\n'.join(new_lines)
    
    # Write the result
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return blocks_fixed, original_content != content


if __name__ == '__main__':
    filepath = '/home/ziontech922/GESTOR-MANUTECAO/app.py'
    blocks_fixed, changed = refactor_file(filepath)
    print(f"Blocks fixed: {blocks_fixed}")
    print(f"File changed: {changed}")
