;; Java tree-sitter query for metrics

(method_declaration) @function
(constructor_declaration) @function

(class_declaration) @class
(interface_declaration) @class
(enum_declaration) @class
(record_declaration) @class
(annotation_type_declaration) @class

(if_statement) @decision
(for_statement) @decision
(enhanced_for_statement) @decision
(while_statement) @decision
(do_statement) @decision
(switch_expression) @decision
(catch_clause) @decision
(ternary_expression) @decision
(binary_expression
  operator: ["&&" "||"]) @decision

(import_declaration) @import
