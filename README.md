# TimeSheet
Definition
- Requirement Diagram
- Activity Diagram
- Structural Diagram

# Variable Definition
    Variable declaration naming convention
    <mandatory: type>_<optional: unit><mandatory: variable_name> - e.g. str_date_startpoint

        type    |    description
        ---------------------------
        obj     |   complex datatype
        str     |   string
        int     |   integer
        db      |   double       
        bo      |   boolean

CHANGES :
    REF NO  VERSION DATE    WHO     DETAIL
            A.00.01 220126  DH      Function CalcHuffman corrected

# Commit Template
Commit change template naming convention
    <mandatory: Branch Change Type><mandatory: file/feature/change_type>_<mandatory: item_name>|<mandatory: description>
        - FCT: Function Change Types
            - A: Architecture Change
            - I:Interface Change
            - F: Functional Change
            - V: Variable Change
        - INF: Infrastructure Change Types
            - D: Documentation Change
            - R: Renaming Change
            - L: Location Change

# Branch Template
Branch change template naming convention
    <mandatory: Function/Infrastructure Change>|<mandatory: description>
        - FCT: Function Change Types
        - INF: Infrastructure Change Types

