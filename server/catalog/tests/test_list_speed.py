"""NFR2.1 / NFR-AC1: the models list answers in under 1 second at 1,000 models."""

import statistics
import time

import psycopg


def fill(url, n=1000):
    with psycopg.connect(url) as conn:
        conn.execute(
            "insert into models (model_key, model_id, first_imported_at) "
            "select 'org' || mod(i, 50) || '/model-' || i, 'org' || mod(i, 50) || '/model-' || i, now() "
            "from generate_series(1, %s) i",
            (n,),
        )
        conn.execute(
            "insert into model_summary (model_key, model_id, latest_commit, state, task, library, "
            "license, language, parameter_count, downloads, likes, last_modified_at, created_at, "
            "imported_at, imported_by_id, imported_by_name, tags, ids_text, search_vector) "
            "select m.model_key, m.model_id, repeat('a', 40), 'imported', "
            "(array['text-generation','fill-mask','translation','summarization'])[1 + mod(i, 4)], "
            "(array['transformers','gguf','diffusers'])[1 + mod(i, 3)], "
            "(array['mit','apache-2.0','llama3'])[1 + mod(i, 3)], array['en'], "
            "(i * 7919)::bigint * 1000, i * 13, i, now() - (i || ' hours')::interval, now(), "
            "now() - (i || ' minutes')::interval, 'u' || mod(i, 7), 'user' || mod(i, 7), "
            "array['tag' || mod(i, 30), 'chat'], m.model_id || ' tag' || mod(i, 30) || ' chat', "
            "to_tsvector('english', 'a quantized model number ' || i || ' for the tests') "
            "from models m join generate_series(1, %s) i "
            "on m.model_key = 'org' || mod(i, 50) || '/model-' || i",
            (n,),
        )
        conn.execute("analyze model_summary")
        conn.commit()


def test_the_list_meets_the_speed_target_at_1000_models(store, fresh_database):
    fill(fresh_database)
    queries = [
        {},
        {"task": "text-generation"},
        {"library": "gguf", "sort": "likes"},
        {"sort": "importedAt"},
        {"importedBy": "u3", "sort": "lastModified"},
        {"q": "quantized"},
        {"q": "model-77"},
        {"q": "chat tag7"},
        {"parameters": "12b", "page": 2},
    ]
    assert store.list_models({})["total"] == 1000
    times = []
    for i in range(100):
        start = time.perf_counter()
        store.list_models(queries[i % len(queries)])
        times.append(time.perf_counter() - start)
    times.sort()
    p95 = times[94]
    print(f"list p50={statistics.median(times) * 1000:.0f} ms p95={p95 * 1000:.0f} ms")
    assert sum(t < 1.0 for t in times) >= 95
