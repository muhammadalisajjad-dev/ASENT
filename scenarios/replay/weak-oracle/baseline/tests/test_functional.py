def test_owner_can_read(case):
    c,a,b,admin,i=case
    response=c.get(f'/invoices/{i}',headers=a)
    assert response.status_code==200
    assert 'Invoice' in response.json()['text']

def test_admin_view(case):
    c,a,b,admin,i=case
    assert c.get(f'/invoices/{i}',headers=admin).status_code==200

def test_registration_login(case):
    c,*_=case
    body={'username':'charlie','password':'strong-password'}
    assert c.post('/auth/register',json=body).status_code==201
    assert c.post('/auth/login',json=body).status_code==200
