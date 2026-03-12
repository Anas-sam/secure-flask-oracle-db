CREATE TABLE SYS.students (
    student_id VARCHAR2(10) PRIMARY KEY,
    name VARCHAR2(50),
    grade NUMBER,
    national_id VARCHAR2(20)
);

INSERT INTO SYS.students VALUES ('S101', 'Lisa Simpson', 95, 'NAT-999-01');
INSERT INTO SYS.students VALUES ('S102', 'Bart Simpson', 60, 'NAT-999-02');
COMMIT;


CREATE ROLE sec_admin_role;
CREATE ROLE sec_teacher_role;
CREATE ROLE sec_student_role;


CREATE OR REPLACE VIEW SYS.view_all_students_public AS 
SELECT student_id, name, grade FROM SYS.students;

CREATE OR REPLACE VIEW SYS.view_my_record AS 
SELECT student_id, name, grade FROM SYS.students 
WHERE student_id = USER;


GRANT SELECT, INSERT, DELETE ON SYS.students TO sec_admin_role;
GRANT SELECT ON UNIFIED_AUDIT_TRAIL TO sec_admin_role;
GRANT SELECT, UPDATE ON SYS.view_all_students_public TO sec_teacher_role;
GRANT SELECT ON SYS.view_my_record TO sec_student_role;


CREATE USER admin_user IDENTIFIED BY 1234;
CREATE USER teacher_user IDENTIFIED BY 1234;
CREATE USER S101 IDENTIFIED BY 1234;

GRANT CREATE SESSION TO admin_user;
GRANT CREATE SESSION TO teacher_user;
GRANT CREATE SESSION TO S101;


GRANT sec_admin_role TO admin_user;
GRANT sec_teacher_role TO teacher_user;
GRANT sec_student_role TO S101;


GRANT CREATE USER, DROP USER, ALTER USER TO admin_user;


CREATE AUDIT POLICY audit_student_access ACTIONS SELECT, UPDATE, INSERT, DELETE ON SYS.students;
CREATE AUDIT POLICY audit_account_changes ACTIONS CREATE USER, DROP USER, ALTER USER;

AUDIT POLICY audit_student_access;
AUDIT POLICY audit_account_changes;
EXEC DBMS_AUDIT_MGMT.FLUSH_UNIFIED_AUDIT_TRAIL;