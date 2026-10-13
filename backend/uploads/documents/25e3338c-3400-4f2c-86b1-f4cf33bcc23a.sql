SELECT * FROM ankitadb_1.marks;

select * from student;

INSERT INTO marks VALUES
(1, 1, 'Math', 85, '2024-01-10'),
(2, 1, 'Science', 78, '2024-01-12'),
(3, 2, 'Math', 92, '2024-01-10'),
(4, 2, 'Science', 88, '2024-01-12'),
(5, 3, 'Math', 60, '2024-01-10'),
(6, 3, 'Science', 55, '2024-01-12'),
(7, 4, 'Math', 70, '2024-01-10'),
(8, 5, 'Math', 40, '2024-01-10'),
(9, 5, 'Science', 35, '2024-01-12'),
(10, 1, 'Math', 90, '2024-02-10'),  
(11, 2, 'Math', 95, '2024-02-10'),
(12, 3, 'Math', 65, '2024-02-10');

select * from marks;


-- LEFT JOIN:
select s.stu_id, s.stu_name, m.subject, m.marks from student s 
left join marks m on s.stu_id= m.stu_id;

select s.stu_id, s.stu_name from student s 
left join marks m on s.stu_id= m.stu_id is null;

-- INNER JOIN: (Students who have marks in at least one subject)
select distinct s.stu_id, s.stu_name from student s inner join marks m on s.stu_id= m.stu_id;


-- Student names with number of subjects (left join)
select s.stu_name, count(m.subject) as total_subjects from student s
left join marks m on s.stu_id= m.stu_id group by s.stu_name;


-- Students who scored more than 75 in any subject
select distinct s.stu_name from student s join marks m on 
s.stu_id= m.stu_id where m.marks > 75;


-- Students with marks in more than 2 subjects
SELECT s.stu_name FROM student s JOIN marks m  ON s.stu_id = m.stu_id
GROUP BY s.stu_name HAVING COUNT(DISTINCT m.subject) > 2;

-- Students with their highest marks
SELECT s.stu_name, MAX(m.marks) AS highest_marks
FROM student s JOIN marks m  ON s.stu_id = m.stu_id
GROUP BY s.stu_name;


-- Average marks per student
SELECT s.stu_name, AVG(m.marks) AS avg_marks
FROM student s JOIN marks m  ON s.stu_id = m.stu_id
GROUP BY s.stu_name;


-- Students who scored the same marks as another student
SELECT DISTINCT s1.stu_name, m1.marks
FROM student s1
JOIN marks m1 ON s1.stu_id = m1.stu_id
JOIN marks m2 
ON m1.marks = m2.marks 
AND m1.stu_id <> m2.stu_id;


-- Students with at least one subject < 40
SELECT DISTINCT s.stu_name
FROM student s
JOIN marks m 
ON s.stu_id = m.stu_id
WHERE m.marks < 40;