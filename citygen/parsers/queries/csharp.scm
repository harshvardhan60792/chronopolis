;; C# tree-sitter query for metrics

(method_declaration) @function
(local_function_statement) @function
(constructor_declaration) @function
(destructor_declaration) @function

(class_declaration) @class
(interface_declaration) @class
(struct_declaration) @class
(record_declaration) @class
(enum_declaration) @class

(if_statement) @decision
(for_statement) @decision
(foreach_statement) @decision
(while_statement) @decision
(do_statement) @decision
(switch_section) @decision
(switch_expression_arm) @decision
(catch_clause) @decision
(conditional_expression) @decision
(binary_expression
  operator: ["&&" "||"]) @decision

(using_directive) @import
