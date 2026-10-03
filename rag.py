"""MedlinePlus-only ingestion and top-three retrieval for Ruhma's JSONL."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DIMENSION = 384
COLLECTION = 'faithfulmed_medlineplus_minilm_v1'

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data): self.parts.append(data)

def plain(text):
    parser = PlainText(); parser.feed(text)
    return re.sub(r'\s+([.,;:!?])', r'\1', ' '.join(unescape(' '.join(parser.parts)).split()))

def valid_vector(vector):
    return (isinstance(vector, list) and len(vector) == DIMENSION
            and all(type(x) in (int, float) and math.isfinite(x) for x in vector)
            and any(x != 0 for x in vector))

def read_embeddings(path):
    """Filter before indexing; fail on invalid MedlinePlus records, never silently drop them."""
    records = {}; sources = Counter(); duplicates = 0
    with Path(path).open(encoding='utf-8-sig') as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip(): continue
            try: row = json.loads(line)
            except ValueError as exc: raise ValueError(f'Invalid JSON on line {number}') from exc
            if not isinstance(row, dict): raise ValueError(f'Line {number}: expected object')
            metadata = row.get('Metadata')
            if not isinstance(metadata, dict): raise ValueError(f'Line {number}: missing Metadata object')
            source = metadata.get('source', 'missing'); sources[str(source)] += 1
            if source != 'MedlinePlus': continue
            term = row.get('Medical_Term'); definition = row.get('Lay_Language_Definition')
            embedded_text = row.get('Text_to_Embed'); url = metadata.get('url')
            if not all(isinstance(x, str) and x.strip() for x in (term, definition, embedded_text, url)):
                raise ValueError(f'Line {number}: missing term, definition, embedded text, or source URL')
            if not plain(definition): raise ValueError(f'Line {number}: empty definition after HTML removal')
            if not valid_vector(row.get('Embedding')):
                raise ValueError(f'Line {number}: expected finite nonzero {DIMENSION}-dimensional vector')
            # Use the exact text Ruhma embedded; cleaning must not change its vector association.
            ident = hashlib.sha256(json.dumps([url, term, embedded_text], ensure_ascii=False).encode()).hexdigest()
            record = {'id': ident, 'text': embedded_text, 'embedding': row['Embedding'],
                      'metadata': {'source': source, 'url': url, 'source_id': url,
                                   'term': term, 'definition': plain(definition), 'chunk_index': 0}}
            if ident in records:
                if records[ident]['embedding'] != record['embedding']:
                    raise ValueError(f'Line {number}: duplicate text has different vectors')
                duplicates += 1
            records[ident] = record
    if not records: raise ValueError('No valid MedlinePlus records found')
    return list(records.values()), {'total_records': sum(sources.values()), 'sources': dict(sources),
                                   'indexed_records': len(records), 'duplicate_medlineplus_records': duplicates,
                                   'embedding_model': MODEL, 'dimension': DIMENSION}

def open_collection(db_path, create=False):
    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
    expected = {'embedding_model': MODEL, 'dimension': DIMENSION, 'schema_version': 1, 'hnsw:space': 'cosine'}
    target = (client.get_or_create_collection(COLLECTION, metadata=expected, embedding_function=None)
              if create else client.get_collection(COLLECTION, embedding_function=None))
    if any((target.metadata or {}).get(k) != v for k,v in expected.items()):
        raise ValueError('Collection model/schema mismatch. Use a separate database for other embeddings.')
    return target

def ingest(path, db_path):
    records, report = read_embeddings(path)  # Validate the entire input before writing.
    target = open_collection(db_path, create=True)
    for start in range(0, len(records), 100):
        group = records[start:start+100]
        target.upsert(ids=[r['id'] for r in group], documents=[r['text'] for r in group],
                      embeddings=[r['embedding'] for r in group], metadatas=[r['metadata'] for r in group])
    report.update(collection=COLLECTION, collection_count=target.count())
    return report

def query_vector(vector, target, top_k=3):
    if type(top_k) is not int or top_k < 1: raise ValueError('top_k must be a positive integer')
    if not valid_vector(vector): raise ValueError('Query vector must match the 384-dimensional MiniLM index')
    if not target.count(): return []
    found = target.query(query_embeddings=[vector], n_results=min(top_k,target.count()),
                         include=['documents','metadatas','distances'])
    return [{'id': ident, 'text': plain(doc), 'definition': meta['definition'],
             'metadata': meta, 'distance': distance}
            for ident,doc,meta,distance in zip(found['ids'][0],found['documents'][0],
                                               found['metadatas'][0],found['distances'][0])]

_model = None
def embed_queries(texts):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL)
    return _model.encode(texts, normalize_embeddings=False).tolist()

def retrieve(query, db_path='./chroma_data', top_k=3):
    """Framework-neutral interface. Return source-attributed records, not generated advice."""
    if not isinstance(query,str) or not query.strip(): raise ValueError('query must be nonempty')
    return query_vector(embed_queries([query])[0], open_collection(db_path), top_k)

class TextQueryCollection:
    """Match Rafi's existing query_texts adapter without Chroma's default embedder."""
    def __init__(self, db_path='./chroma_data'):
        self.target = open_collection(db_path)
    def query(self, *, query_texts, n_results=3, **kwargs):
        if type(n_results) is not int or n_results < 1: raise ValueError('n_results must be positive')
        if not self.target.count():
            return {k:[[] for _ in query_texts] for k in ('ids','documents','metadatas','distances')}
        kwargs.setdefault('include',['documents','metadatas','distances'])
        return self.target.query(query_embeddings=embed_queries(query_texts),
                                 n_results=min(n_results,self.target.count()), **kwargs)

def format_context(results):
    return '\n\n'.join(f"[{i}] {r['metadata']['term']}\n{r['definition']}\nSource: {r['metadata']['url']}"
                       for i,r in enumerate(results,1))

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('ingest'); a.add_argument('file'); a.add_argument('--db',default='./chroma_data')
    a=sub.add_parser('search'); a.add_argument('query'); a.add_argument('--db',default='./chroma_data'); a.add_argument('--top-k',type=int,default=3)
    a=sub.add_parser('audit'); a.add_argument('file')
    args=p.parse_args()
    if args.command=='ingest': output=ingest(args.file,args.db)
    elif args.command=='audit': output=read_embeddings(args.file)[1]
    else: output=retrieve(args.query,args.db,args.top_k)
    print(json.dumps(output,indent=2,allow_nan=False))
if __name__=='__main__': main()
