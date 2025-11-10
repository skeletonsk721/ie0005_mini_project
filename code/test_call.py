from api_core import call_model

if __name__ == '__main__':
    try:
        out = call_model('请写一首 4 行中文俳句关于秋天。')
        print('MODEL OUTPUT:\n', out)
    except Exception as e:
        print('CALL FAILED:', e)
