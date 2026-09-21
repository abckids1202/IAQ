"""Single-process pilot journey: real API contracts, no external charges/mail."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from app import access
from app import main as api
from app.domain import DOMAINS, score_domains


def headers(token):
    return {"X-IAQ-Session": token}


def complete(client, auth):
    session = client.post('/assessments/iaq-cognitive/sessions', json={"mode": "complete", "age_band": "18-22"}, headers=auth).json()
    sid = session['id']
    assert session['question_count'] == 48
    assert client.post(f'/sessions/{sid}/start', headers=auth).status_code == 200
    domains = Counter()
    for index in range(48):
        public = client.get(f'/sessions/{sid}/next-item', headers=auth).json()
        assert not ({'answer', 'answer_index', 'rule', 'explanation', 'provenance'} & public.keys())
        item = api.ITEMS[public['id']]
        domains[item['domain']] += 1
        response = {'item_id': item['id'], 'presented_order': index, 'response_time_ms': 5000}
        if item.get('memory_response_type'):
            response.update(response_type=item['memory_response_type'], response=json.loads(item['answer']))
            assert client.post(f'/sessions/{sid}/responses', json=response, headers=auth).status_code == 409
            assert client.post(f'/sessions/{sid}/items/{item["id"]}/begin-recall', headers=auth).status_code == 200
            recalled = client.get(f'/sessions/{sid}/next-item', headers=auth).json()
            assert 'visual' not in recalled and 'image_url' not in recalled
            # Repeated start must not replay the study stimulus either.
            assert 'visual' not in client.post(f'/sessions/{sid}/start', headers=auth).json()['next_item']
            if item['memory_response_type'] == 'cell_set':
                response['response'].reverse()
        else:
            response['answer_index'] = item['options'].index(item['answer'])
        saved = client.post(f'/sessions/{sid}/responses', json=response, headers=auth)
        assert saved.status_code == 200, saved.text
        assert client.post(f'/sessions/{sid}/responses', json=response, headers=auth).json()['duplicate']
    assert domains == Counter({domain: 8 for domain in DOMAINS})
    result = client.post(f'/sessions/{sid}/submit', headers=auth).json()
    assert client.post(f'/sessions/{sid}/submit', headers=auth).json()['id'] == result['id']
    assert client.get(f'/sessions/{sid}/next-item', headers=auth).json() == {'complete': True}
    assert client.post(f'/sessions/{sid}/resume', headers=auth).status_code == 409
    return result['id']


def test_guest_score_manual_payment_selected_report_and_verified_claim(monkeypatch):
    monkeypatch.setenv('IAQ_AUTH_MODE', 'development')
    monkeypatch.setenv('IAQ_ENV', 'development')
    monkeypatch.setenv('IAQ_GUEST_ASSESSMENT_ENABLED', 'true')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    client = TestClient(api.app)
    guest = client.post('/auth/guest').json()
    auth = headers(guest['session_token'])
    rid = complete(client, auth)
    hidden = client.get(f'/results/{rid}', headers=auth).json()
    assert hidden['identity_required'] and hidden['iq_score'] == 130
    email = f'{uuid4().hex}@example.com'
    captured = client.post('/me/identity', json={'result_id': rid, 'email': email, 'display_name': 'Pilot Tester', 'age_band': '18-22', 'granted': True}, headers=auth)
    assert captured.status_code == 200
    assert captured.json()['user']['is_guest']
    free = client.get(f'/results/{rid}', headers=auth).json()
    assert free['iq_score'] == 130 and free['full_access'] is False
    assert free['domain_scores'] == {} and 'composite' not in free and 'quality' not in free
    assert client.post('/ai/directions', json={'result_id': rid}, headers=auth).status_code == 402
    order_body = {'product_id': 'iaq-complete', 'result_id': rid}
    order = client.post('/orders', json=order_body, headers=auth).json()
    assert order['total_minor'] == 50000 and order['currency'] == 'IDR'
    assert client.post('/orders', json=order_body, headers=auth).json()['id'] == order['id']
    proof = client.post(f'/orders/{order["id"]}/payment-proof', headers={**auth, 'Idempotency-Key': uuid4().hex}, files={'receipt': ('receipt.pdf', b'%PDF-1.4\nTEST ONLY', 'application/pdf')})
    assert proof.status_code == 200
    proof_id = proof.json()['id']
    duplicate_proof = client.post(f'/orders/{order["id"]}/payment-proof', headers={**auth, 'Idempotency-Key': uuid4().hex}, files={'receipt': ('other.pdf', b'%PDF-1.4\nOTHER', 'application/pdf')})
    assert duplicate_proof.status_code == 409
    assert client.get(f'/results/{rid}', headers=auth).json()['full_access'] is False
    assert client.post(f'/admin/payment-proofs/{proof_id}/approve', json={'note': 'test'}, headers=auth).status_code == 403
    admin = headers(access.issue_dev_session('demo-admin'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        approved = list(pool.map(lambda _: client.post(f'/admin/payment-proofs/{proof_id}/approve', json={'note': 'Test fixture: verified manually'}, headers=admin), range(2)))
    assert all(response.status_code == 200 for response in approved)
    full = client.get(f'/results/{rid}', headers=auth).json()
    assert full['full_access'] and full['iq_score'] == free['iq_score']
    assert set(full['domain_scores'].values()) == {100}
    assert client.post(f'/ai/results/{rid}/interpretation', headers=auth).status_code == 200
    interest = {'R': 40, 'I': 90, 'A': 80, 'S': 30, 'E': 20, 'C': 60}
    assert client.post('/questionnaires/compass-v1/responses', json={'result_id': rid, 'responses': interest}, headers=auth).status_code == 200
    assert client.post('/ai/directions', json={'result_id': rid}, headers=auth).json()['directions']
    # Another result from the very same user stays locked.
    other = complete(client, auth)
    assert client.get(f'/results/{other}', headers=auth).json()['full_access'] is False
    assert client.post('/ai/directions', json={'result_id': other}, headers=auth).status_code == 402
    stranger = headers(client.post('/auth/guest').json()['session_token'])
    assert client.get(f'/results/{rid}', headers=stranger).status_code == 404
    assert client.get(f'/orders/{order["id"]}/status', headers=stranger).status_code == 404
    # Claim requires both verified sign-in and possession of the guest token.
    assert client.post('/auth/otp/request', json={'email': email}).status_code == 200
    signed = client.post('/auth/otp/verify', json={'email': email, 'code': '123456'}).json()
    account = headers(signed['session_token'])
    claim = client.post('/results/claim', json={'result_id': rid, 'guest_token': guest['session_token']}, headers=account)
    assert claim.status_code == 200, claim.text
    assert client.get(f'/results/{rid}', headers=account).json()['full_access']
    assert client.get(f'/results/{rid}', headers=auth).status_code == 404
    assert client.get(f'/me/interests?result_id={rid}', headers=account).json()['scores'] == interest


def test_score_rounds_once_ignores_duplicates_and_withholds_sparse_evidence():
    mapping = {f'{domain}-{i}': domain for domain in DOMAINS for i in range(8)}
    keys = {key: 'yes' for key in mapping}
    for correct in range(49):
        responses = [{'item_id': key, 'answer': 'yes' if i < correct else 'no', 'response_time_ms': 6000} for i, key in enumerate(mapping)]
        result = score_domains(responses + responses[:1], mapping, keys)
        assert result.iq_score == round(70 + correct / 48 * 60)
        assert sum(metric['answered'] for metric in result.domain_metrics.values()) == 48
        assert result.confidence != 'high' and result.norm_version is None
    sparse = score_domains(responses[:12], mapping, keys)
    assert sparse.iq_score is None and sparse.confidence == 'low'
    assert 'incomplete_assessment' in sparse.quality_warnings


def test_order_enforcement_concurrency_and_expiry():
    client = TestClient(api.app)
    auth = headers(client.post('/auth/guest').json()['session_token'])
    session = client.post('/assessments/iaq-cognitive/sessions', json={'mode': 'complete'}, headers=auth).json()
    sid = session['id']
    client.post(f'/sessions/{sid}/start', headers=auth)
    state = api.SESSIONS[sid]
    second = state['item_order'][1]
    assert client.post(f'/sessions/{sid}/responses', json={'item_id': second, 'answer_index': 0, 'presented_order': 1}, headers=auth).status_code == 409
    first = api.ITEMS[state['item_order'][0]]
    body = {'item_id': first['id'], 'answer_index': 0, 'presented_order': 0}
    if first.get('memory_response_type'):
        client.post(f'/sessions/{sid}/items/{first["id"]}/begin-recall', headers=auth)
        body.update(response_type=first['memory_response_type'], response=json.loads(first['answer']))
    with ThreadPoolExecutor(max_workers=4) as pool:
        replies = list(pool.map(lambda _: client.post(f'/sessions/{sid}/responses', json=body, headers=auth), range(4)))
    assert all(reply.status_code == 200 for reply in replies)
    assert len(state['responses']) == 1
    state['deadline_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    assert client.get(f'/sessions/{sid}/next-item', headers=auth).json()['expired']
    assert client.post(f'/sessions/{sid}/responses', json=body, headers=auth).status_code == 409
    assert client.post(f'/sessions/{sid}/submit', headers=auth).status_code == 200
