;; C tree-sitter query for metrics

(function_definition) @function

(struct_specifier) @class
(union_specifier) @class
(enum_specifier) @class

(if_statement) @decision
(for_statement) @decision
(while_statement) @decision
(do_statement) @decision
(switch_statement) @decision
(conditional_expression) @decision
(binary_expression
  operator: ["&&" "||"]) @decision

(preproc_include) @import
