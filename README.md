# TimeSheetAlgo

## Description
The TimeSheetAlgo is inteded to automate the manual timedata extraction, timedata documentation and AZESheet creation.

## Algo Analysis

### Stakeholder Analysis
![Alt](00_doc/Architecture_Models-01_Analysis_bdd.drawio.png)

### Stakeholder Analysis
![Alt](00_doc/Architecture_Models-01_Analysis_ibd.drawio.png)

### Use-Cases
![Alt](00_doc/Architecture_Models-01_Analysis_uc.drawio.png)

## Variable Definition
    Variable declaration naming convention
    <mandatory: type>_<optional: unit><mandatory: variable_name> - e.g. str_date_startpoint

        type    |    description
        ---------------------------
        fil     |   file
        obj     |   complex datatype
        str     |   string
        int     |   integer
        db      |   double       
        bo      |   boolean

## Branch Template
    Branch change template naming convention
    <mandatory: Function/Infrastructure Change>|<mandatory: description>
        - FCT: Function Change Types
        - INF: Infrastructure Change Types

        Example: INF|Documentation

## Commit Template
    Commit change template naming convention
    <mandatory: Branch Change Type>_<mandatory: change_type>|<optional: file></><mandatory: change/feature/description>
        - FCT: Function Change Types
            - A: Architecture Change
            - I: Interface Change
            - F: Functional Change
            - V: Variable Change
            - O: Optimazation Change
        - INF: Infrastructure Change Types
            - D: Documentation Change
            - R: Renaming Change
            - L: Location Change

        Example: INF_F|README.md/Split Commit and Branch Template
