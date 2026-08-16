;; C/C++ tree-sitter query for metrics

(function_definition) @function

(class_specifier) @class
(struct_specifier) @class
(union_specifier) @class
(enum_specifier) @class

(if_statement) @decision
(for_statement) @decision
(for_range_loop) @decision
(while_statement) @decision
(do_statement) @decision
(case_statement) @decision
(catch_clause) @decision
(conditional_expression) @decision
(binary_expression
  operator: ["&&" "||"]) @decision

(preproc_include) @import
