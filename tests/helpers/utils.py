from django.test.utils import CaptureQueriesContext


def queries_to_str(queries: CaptureQueriesContext) -> str:
    result = "\n"
    for index, query in enumerate(queries.captured_queries, start=1):
        raw_query = query["sql"].replace("`", "")  # remove unnecessary formatting
        result += f"\n\n#{index} {raw_query}"

    return result
