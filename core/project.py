import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def new_project(name='Novo projeto'):
    return dict(versao=1, id=str(uuid.uuid4()), nome=name, revisao='00', codigo='PLANO-RMT',
                trechos=[], bobinas=[], avisos=[], criterios_confirmados=False,
                criterios=dict(sobra_minima=50, peso_cortes=1000, peso_bobinas=100, peso_perda=1), plano=None)


def demo():
    p = new_project('Parque demonstração')
    for phase in ('A', 'B', 'C'):
        for i, distance in enumerate([240.35, 185.15, 320.42, 210.1, 275.38, 190.2], 1):
            p['trechos'].append(dict(id=f'T{i:02d}-{phase}', parque='DEMO-01', circuito='C01', nivel='1',
                                    fase=phase, condutor='CA MAGNOLIA 954 MCM', tipo='AÉREO', rota='Principal',
                                    ordem=i, de=f'E{i:02d}', para=f'E{i+1:02d}', linear=distance, folga=.05,
                                    reserva=0, corte_fim='PROIBIDO' if i == 2 else 'PERMITIDO',
                                    fixa='', bobina_original='', observacao='Travessia E02–E04' if i in (2,3) else ''))
    for i in range(1, 5):
        p['bobinas'].append(dict(id=f'DEMO-MAG-{i:03d}', condutor='CA MAGNOLIA 954 MCM', tipo='AÉREO',
                                nominal=1500, real=1487 if i == 1 else None, utilizado=0))
    p['criterios_confirmados'] = True
    return p


def connection():
    path = Path(os.environ.get('RMT_DB_PATH', 'data/projetos.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT, updated TEXT, body TEXT)')
    return db


def save(project):
    project['atualizado'] = datetime.now(timezone.utc).isoformat()
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO projects VALUES (?, ?, ?, ?)',
                   (project['id'], project['nome'], project['atualizado'], json.dumps(project, ensure_ascii=False, allow_nan=False)))


def saved_projects():
    with connection() as db:
        return db.execute('SELECT id, name, updated FROM projects ORDER BY updated DESC').fetchall()


def load(ident):
    with connection() as db:
        row = db.execute('SELECT body FROM projects WHERE id=?', (ident,)).fetchone()
    if row is None:
        raise ValueError('Projeto não encontrado.')
    return json.loads(row[0])


def restore(content):
    p = json.loads(content)
    if p.get('versao') != 1 or not isinstance(p.get('trechos'), list) or not isinstance(p.get('bobinas'), list):
        raise ValueError('Arquivo de projeto inválido ou versão não suportada.')
    defaults = new_project()
    defaults.update(p)
    defaults['id'] = str(uuid.uuid4())
    defaults['plano'] = None  # Revalidar resultados após restauração de dados externos.
    return defaults
