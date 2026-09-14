"""Fail closed on extra model-visible context in native loopback captures."""
import re
import runtime

def check(capture,prompt):
    requests=capture['requests']
    if not requests or capture['timed_out']:raise ValueError('NO_COMPLETE_CONTEXT_CAPTURE')
    for request in requests:
        b=request['body']
        if b.get('model')!=runtime.MODELS[capture['annotator']]:raise ValueError('MODEL_CHANGED')
        if b.get('tools')!=[]:raise ValueError('TOOLS_PRESENT')
        system=b.get('system')
        if not isinstance(system,list) or len(system)!=3:raise ValueError('SYSTEM_BLOCKS_CHANGED')
        texts=[v.get('text') for v in system]
        if not re.fullmatch(r'x-anthropic-billing-header: cc_version=2\.1\.270\.[a-z0-9]+; cc_entrypoint=sdk-cli;',texts[0] or ''):raise ValueError('BILLING_HEADER_CHANGED')
        if texts[1]!="You are a Claude agent, built on Anthropic's Claude Agent SDK." or texts[2]!=runtime.SYSTEM:raise ValueError('SYSTEM_CONTEXT_CHANGED')
        for block in system:
            if set(block)-{'type','text','cache_control'} or block.get('type')!='text':raise ValueError('EXTRA_SYSTEM_DATA')
            if 'cache_control' in block and block['cache_control']!={'type':'ephemeral'}:raise ValueError('EXTRA_CACHE_DATA')
        messages=b.get('messages')
        if not isinstance(messages,list) or len(messages)!=2:raise ValueError('EXTRA_MESSAGES')
        if messages[0]!={'role':'user','content':prompt}:raise ValueError('PROMPT_CHANGED')
        extra=messages[1]
        if set(extra)!={'role','content'} or extra['role']!='system' or len(extra['content'])!=1:raise ValueError('EXTRA_ENVIRONMENT')
        block=extra['content'][0]
        if set(block)-{'type','text','cache_control'} or block.get('type')!='text':raise ValueError('EXTRA_ENVIRONMENT_DATA')
        model=runtime.MODELS[capture['annotator']]
        pattern=(r'# Environment\nYou have been invoked in the following environment: \n - Primary working directory: '+
                 re.escape(capture['workspace'])+r'\n - Is a git repository: false\n - Platform: darwin\n - Shell: zsh\n - OS Version: Darwin [0-9.]+\n\n'+
                 r'You are powered by the model named [A-Za-z0-9 .]+\. The exact model ID is '+re.escape(model)+
                 r'\. Assistant knowledge cutoff is [A-Za-z]+ [0-9]{4}\.\n\nToday\x27s date is [0-9]{4}-[0-9]{2}-[0-9]{2}\.')
        environment_text=block.get('text','')
        # Sonnet wraps each of these same three native sections in system-reminder.
        if capture['annotator']=='A':
            environment_text=environment_text.replace('<system-reminder>\n','').replace('\n</system-reminder>','')
        if not re.fullmatch(pattern,environment_text):raise ValueError('ENVIRONMENT_TEXT_CHANGED')
        if 'cache_control' in block and block['cache_control']!={'type':'ephemeral'}:raise ValueError('EXTRA_ENVIRONMENT_CACHE_DATA')
    return {'ok':True,'requests_checked':len(requests),'tools':0,'context':'prompt + pinned system blocks + bounded native environment block'}
