from functools import partial

from sqlfmt import actions
from sqlfmt.rule import Rule
from sqlfmt.rules.clone import CLONE as CLONE
from sqlfmt.rules.common import (
    ALTER_DROP_FUNCTION,
    ALTER_WAREHOUSE,
    CREATE_CLONABLE,
    CREATE_FUNCTION,
    CREATE_WAREHOUSE,
    PRAGMA_SET_CALL,
    group,
)
from sqlfmt.rules.core import CORE as CORE
from sqlfmt.rules.function import FUNCTION as FUNCTION
from sqlfmt.rules.grant import GRANT as GRANT
from sqlfmt.rules.jinja import JINJA as JINJA  # noqa
from sqlfmt.rules.pragma import PRAGMA as PRAGMA
from sqlfmt.rules.unsupported import UNSUPPORTED as UNSUPPORTED
from sqlfmt.rules.warehouse import WAREHOUSE as WAREHOUSE
from sqlfmt.tokens import TokenType

MAIN = [
    *CORE,
    Rule(
        name="star_columns",
        priority=409,  # star is 410
        pattern=group(r"\*columns") + group(r"\(", r"$"),
        action=partial(actions.add_node_to_buffer, token_type=TokenType.NAME),
    ),
    Rule(
        name="statement_start",
        priority=1000,
        pattern=group(r"case") + group(r"\W", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.STATEMENT_START
            ),
        ),
    ),
    Rule(
        name="statement_end",
        priority=1010,
        pattern=group(r"end") + group(r"\W", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.safe_add_node_to_buffer,
                token_type=TokenType.STATEMENT_END,
                fallback_token_type=TokenType.NAME,
            ),
        ),
    ),
    Rule(
        # There are some function names in some dialects that are the same as
        # word operators in other dialects. Here we lex those as function
        # names IFF the name is immediately followed by a `(` (with no space
        # after the name. Otherwise they are lexed as word_operators by the
        # next rule.
        name="functions_that_overlap_with_word_operators",
        priority=1099,
        pattern=group(
            r"filter",
            r"isnull",
            r"(r|i)?like",
        )
        + group(r"\("),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(actions.add_node_to_buffer, token_type=TokenType.NAME),
        ),
    ),
    Rule(
        name="word_operator",
        priority=1100,
        pattern=group(
            r"as",
            r"(not\s+)?between",
            r"cube",
            r"(not\s+)?exists",
            r"filter",
            r"grouping sets",
            r"(not\s+)?in",
            r"interval",
            r"is(\s+not)?(\s+distinct\s+from)?",
            r"isnull",
            r"(not\s+)?i?like(\s+(any|all))?",
            r"over",
            r"(un)?pivot",
            r"notnull",
            r"(not\s+)?regexp",
            r"(not\s+)?rlike",
            r"rollup",
            r"some",
            r"(not\s+)?similar\s+to",
            r"tablesample",
            r"within\s+group",
        )
        + group(r"\W", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.WORD_OPERATOR
            ),
        ),
    ),
    Rule(
        name="star_replace_exclude",
        priority=1101,
        pattern=group(
            r"exclude",
            r"replace",
        )
        + group(r"\s+\("),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.WORD_OPERATOR
            ),
        ),
    ),
    Rule(
        # a join's using word operator must be followed
        # by parens; otherwise, it's probably a
        # delete's USING, which is an unterminated
        # keyword
        name="join_using",
        priority=1110,
        pattern=group(r"using") + group(r"\s*\("),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.WORD_OPERATOR
            ),
        ),
    ),
    Rule(
        name="on",
        priority=1120,
        pattern=group(r"on") + group(r"\W", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(actions.add_node_to_buffer, token_type=TokenType.ON),
        ),
    ),
    Rule(
        name="boolean_operator",
        priority=1200,
        pattern=group(
            r"and",
            r"or",
            r"not",
        )
        + group(r"\W", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.BOOLEAN_OPERATOR
            ),
        ),
    ),
    Rule(
        name="unterm_keyword",
        priority=1300,
        pattern=group(
            r"with(\s+recursive)?",
            (
                r"select(\s+(as\s+struct|as\s+value))?"
                r"(\s+(all|top\s+\d+|distinct))?"
                # select into is ddl that needs additional handling
                r"(?!\s+into)"
            ),
            r"delete\s+from",
            r"from",
            r"((cross|positional|semi|anti)\s+)?join",
            (
                r"((natural|asof)\s+)?"
                r"((inner|(left|right|full)(\s+(outer|anti))?)\s+)?join"
            ),
            # this is the USING following DELETE, not the join operator
            # (see above)
            r"using",
            r"lateral\s+view(\s+outer)?",
            r"where",
            r"group\s+by",
            r"cluster\s+by",
            r"distribute\s+by",
            r"sort\s+by",
            r"having",
            r"qualify",
            r"window",
            r"order\s+by",
            r"limit",
            r"fetch\s+(first|next)",
            r"for\s+(update|no\s+key\s+update|share|key\s+share)",
            r"when",
            r"then",
            r"else",
            r"partition\s+by",
            r"values",
            # in pg, RETURNING can be the last clause of
            # a DELETE statement
            r"returning",
        )
        + group(r"\W", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.UNTERM_KEYWORD
            ),
        ),
    ),
    Rule(
        name="frame_clause",
        priority=1305,
        pattern=group(r"(range|rows|groups)\s+")
        + group(r"(between\s+)?((unbounded|\d+)\s+(preceding|following)|current\s+row)")
        + group(r"\W", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.UNTERM_KEYWORD
            ),
        ),
    ),
    Rule(
        # BQ arrays use an offset(n) function for
        # indexing that we do not want to match. This
        # should only match the offset in limit ... offset,
        # which must be followed by a space
        name="offset_keyword",
        priority=1310,
        pattern=group(r"offset") + group(r"\s+", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.UNTERM_KEYWORD
            ),
        ),
    ),
    Rule(
        name="set_operator",
        priority=1320,
        pattern=group(
            r"(union|intersect|except|minus)(\s+(all|distinct))?(\s+by\s+name)?",
        )
        + group(r"\W", r"$"),
        action=partial(
            actions.handle_reserved_keyword,
            action=actions.handle_set_operator,
        ),
    ),
    Rule(
        name="explain",
        priority=2000,
        pattern=group(r"explain(\s+(analyze|verbose|using\s+(tabular|json|text)))?")
        + group(r"\W", r"$"),
        action=partial(
            actions.handle_nonreserved_top_level_keyword,
            action=partial(
                actions.add_node_to_buffer, token_type=TokenType.UNTERM_KEYWORD
            ),
        ),
    ),
    Rule(
        name="pragma",
        priority=2005,
        pattern=group(PRAGMA_SET_CALL) + group(r"\W", r"$"),
        action=partial(
            actions.handle_nonreserved_top_level_keyword,
            action=partial(actions.lex_ruleset, new_ruleset=PRAGMA),
        ),
    ),
    Rule(
        name="grant",
        priority=2010,
        pattern=group(r"grant", r"revoke") + group(r"\W", r"$"),
        action=partial(
            actions.handle_nonreserved_top_level_keyword,
            action=partial(actions.lex_ruleset, new_ruleset=GRANT),
        ),
    ),
    Rule(
        name="create_clone",
        priority=2015,
        pattern=group(CREATE_CLONABLE + r"\s+.+?\s+clone") + group(r"\W", r"$"),
        action=partial(
            actions.handle_nonreserved_top_level_keyword,
            action=partial(
                actions.lex_ruleset,
                new_ruleset=CLONE,
            ),
        ),
    ),
    Rule(
        name="create_function",
        priority=2020,
        pattern=group(CREATE_FUNCTION, ALTER_DROP_FUNCTION) + group(r"\W", r"$"),
        action=partial(
            actions.handle_nonreserved_top_level_keyword,
            action=partial(
                actions.lex_ruleset,
                new_ruleset=FUNCTION,
            ),
        ),
    ),
    Rule(
        name="create_warehouse",
        priority=2030,
        pattern=group(
            CREATE_WAREHOUSE,
            ALTER_WAREHOUSE,
        )
        + group(r"\W", r"$"),
        action=partial(
            actions.handle_nonreserved_top_level_keyword,
            action=partial(
                actions.lex_ruleset,
                new_ruleset=WAREHOUSE,
            ),
        ),
    ),
    Rule(
        name="unsupported_ddl",
        priority=2999,
        pattern=group(
            r"alter",
            r"attach\s+rls\s+policy",
            r"cache\s+table",
            r"clear\s+cache",
            r"cluster",
            r"comment",
            r"copy",
            r"create",
            r"deallocate",
            r"declare",
            r"describe",
            r"desc\s+datashare",
            r"desc\s+identity\s+provider",
            r"delete",
            r"detach\s+rls\s+policy",
            r"discard",
            r"do",
            r"drop",
            r"execute",
            r"export",
            r"fetch",
            r"get",
            r"handler",
            r"import\s+foreign\s+schema",
            r"import\s+table",
            # snowflake: "insert into" or "insert overwrite into"
            # snowflake: has insert() function
            # spark: "insert overwrite" without the trailing "into"
            # redshift/pg: "insert into" only
            # bigquery: bare "insert" is okay
            r"insert(\s+overwrite)?(\s+into)?",
            r"list",
            r"lock",
            r"merge",
            r"move",
            # prepare transaction statements are simple enough
            # so we'll allow them
            r"prepare(?!\s+transaction)",
            r"put",
            r"reassign\s+owned",
            r"remove",
            r"rename\s+table",
            r"repair",
            r"security\s+label",
            r"select\s+into",
            r"truncate",
            r"unload",
            r"update",
            r"validate",
        )
        + r"(?!\()"
        + group(r"\W", r"$"),
        action=partial(
            actions.handle_nonreserved_top_level_keyword,
            action=partial(
                actions.lex_ruleset,
                new_ruleset=UNSUPPORTED,
            ),
        ),
    ),
]
