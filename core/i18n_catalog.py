"""Demo/catalog labels stored in English in the database.

`makemessages` picks these up so the Polish UI can translate programme names,
semesters and course titles without rewriting rows.
"""
from django.utils.translation import gettext_lazy as _

# Study programmes
_('Computer Science')
_('Mathematics')
_('Physics')

# Semesters (stored values)
_('Fall')
_('Spring')
_('Summer')

# Departments
_('Administration')

# Course titles
_('Introduction to Computer Science')
_('Database Systems')
_('Web Development')
_('Calculus I')
_('Linear Algebra')
_('Physics I — Mechanics')
_('Data Structures & Algorithms')
_('Statistics & Probability')

# Course descriptions
_('Fundamental concepts of computer science including algorithms, data structures, and programming basics.')
_('Design and implementation of relational databases, SQL, normalization, and transaction management.')
_('Modern web technologies including HTML5, CSS3, JavaScript, and server-side programming.')
_('Limits, derivatives, and integrals of single-variable functions.')
_('Vectors, matrices, linear transformations, eigenvalues and eigenvectors.')
_('Classical mechanics, Newton\'s laws, energy, momentum, and rotational motion.')
_('Advanced data structures, algorithm design, complexity analysis, sorting and searching.')
_('Probability theory, random variables, statistical inference, and hypothesis testing.')
