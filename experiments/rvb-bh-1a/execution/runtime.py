"""Pinned native Claude Code invocation; no model calls at import time."""
import os
VERSIONS={'A':'2.1.270 (Claude Code)','B':'2.1.270 (Claude Code)'}
MODELS={'A':'claude-sonnet-5','B':'claude-opus-5'}
SYSTEM='Annotate the supplied cards only. Use no tools. Return only the requested JSON.'

def command(annotator,cwd):
    return ['claude','--print','--safe-mode','--tools','',
            '--disable-slash-commands','--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
            '--setting-sources','','--settings','{"autoMemoryEnabled":false}',
            '--no-session-persistence','--output-format','stream-json','--verbose',
            '--model',MODELS[annotator],'--effort','medium','--system-prompt',SYSTEM]

def environment():
    env={k:v for k,v in os.environ.items() if k in ('HOME','PATH','USER','LOGNAME','SHELL','LANG','LC_ALL')}
    env.update(CLAUDE_CODE_DISABLE_AUTO_MEMORY='1',CLAUDE_CODE_DISABLE_CLAUDE_MDS='1',
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',DISABLE_AUTOUPDATER='1',
               CLAUDE_CODE_DISABLE_ATTACHMENTS='1')
    return env
