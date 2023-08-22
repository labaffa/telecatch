PHONE_FORM = '''
    <form action='/login' method='post'>
        Phone (international format): <input name='phone' type='text' placeholder='+34600000000'>
        <input type='submit'>
    </form>
'''

CODE_FORM = '''
    <form action='/login' method='post'>
        Telegram code: <input name='code' type='text' placeholder='70707'>
        <input type='submit'>
    </form>
'''

PASSWORD_FORM = '''
    <form action='/login' method='post'>
        Telegram password: <input name='password' type='text' placeholder='your password'>
        <input type='submit'>
    </form>
'''
