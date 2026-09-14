"""Native CLI candidates. No proxy, credentials, or model calls at import time."""
import json
from pathlib import Path

VERSIONS={'A':'codex-cli 0.154.0','B':'2.1.270 (Claude Code)'}
MODELS={'A':'gpt-6-astra','B':'claude-opus-5'}

def command(annotator, cwd):
    if annotator=='B':
        return ['claude','--print','--safe-mode','--tools','',
                '--disable-slash-commands','--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
                '--setting-sources','','--no-session-persistence','--output-format','json',
                '--model',MODELS['B'],'--effort','medium',
                '--system-prompt','Annotate the supplied cards only. Use no tools. Return only the requested JSON.']
    settings=['project_doc_max_bytes=0','web_search="disabled"','tools.view_image=false',
              'model_reasoning_summary="none"','hide_agent_reasoning=true','model_reasoning_effort="medium"',
              'shell_environment_policy.inherit="none"','check_for_update_on_startup=false']
    args=['codex','-a','never']
    for value in settings:args += ['-c',value]
    for feature in ['shell_tool','unified_exec','memories','external_agent_memory_import',
                    'plugins','hooks','apps','multi_agent','multi_agent_v2','shell_snapshot',
                    'browser_use','browser_use_external','computer_use','skill_search','sleep_tool','tool_suggest']:
        args += ['--disable',feature]
    args += ['--enable','skip_host_skill_discovery','exec','--ephemeral','--ignore-user-config',
             '--ignore-rules','--strict-config','--skip-git-repo-check','--sandbox','read-only',
             '--json','--color','never','--model',MODELS['A'],'--cd',str(cwd),'-']
    return args
