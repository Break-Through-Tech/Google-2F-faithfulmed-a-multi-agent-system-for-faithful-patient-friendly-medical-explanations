import unittest

from retrieval import retrieve_context


class FakeCollection:
    def __init__(self, response):
        self.response = response
        self.query_kwargs = None

    def query(self, **kwargs):
        self.query_kwargs = kwargs
        return self.response


class RetrieveContextTests(unittest.TestCase):
    def test_normalizes_chroma_results(self):
        collection = FakeCollection(
            {
                "ids": [["chunk-1", "chunk-2"]],
                "documents": [["Plain-language definition", "Second definition"]],
                "metadatas": [[{"source": "glossary"}, {"source": "guide"}]],
                "distances": [[0.12, 0.31]],
            }
        )

        results = retrieve_context(collection, "hypertension", top_k=2)

        self.assertEqual(collection.query_kwargs["query_texts"], ["hypertension"])
        self.assertEqual(collection.query_kwargs["n_results"], 2)
        self.assertEqual(results[0]["id"], "chunk-1")
        self.assertEqual(results[0]["text"], "Plain-language definition")
        self.assertEqual(results[0]["metadata"], {"source": "glossary"})
        self.assertEqual(results[0]["distance"], 0.12)

    def test_empty_query_does_not_query_collection(self):
        collection = FakeCollection({})

        self.assertEqual(retrieve_context(collection, "  "), [])
        self.assertIsNone(collection.query_kwargs)

    def test_no_results_returns_empty_list(self):
        collection = FakeCollection(
            {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        )

        self.assertEqual(retrieve_context(collection, "rare term"), [])

    def test_metadata_filter_is_forwarded(self):
        collection = FakeCollection(
            {"ids": [["chunk-1"]], "documents": [["Definition"]], "metadatas": [[{}]]}
        )

        retrieve_context(collection, "term", where={"source": "glossary"})

        self.assertEqual(collection.query_kwargs["where"], {"source": "glossary"})

    def test_invalid_top_k_is_rejected(self):
        with self.assertRaises(ValueError):
            retrieve_context(FakeCollection({}), "term", top_k=0)


if __name__ == "__main__":
    unittest.main()