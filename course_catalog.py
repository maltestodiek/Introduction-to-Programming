"""Field-of-study list and shared university course names for the profile form.

The fields are common university degree subjects under the names students use for them
("Business Administration", "Computer Science"). The list is a convenience, not a closed set: a
student can type a field that is missing. Course names come from Supabase and never include who
takes a course.
"""

from pathlib import Path

_file_stamp=Path(__file__).stat().st_mtime  # lets app.py notice when this file changed under a running server

FIELDS_OF_STUDY=sorted([
    'Accounting','Accounting and Finance','Actuarial Science','Aerospace Engineering','African Studies','Agricultural Science','American Studies',
    'Animation','Anthropology','Applied Mathematics','Archaeology','Architecture','Art History','Artificial Intelligence','Asian Studies','Astronomy',
    'Automotive Engineering','Aviation','Banking and Finance','Biochemistry','Bioinformatics','Biology','Biomedical Engineering','Biomedical Science',
    'Biophysics','Biotechnology','Business Administration','Business Analytics','Business and Economics','Business Informatics','Business Law',
    'Chemical Engineering','Chemistry','Civil Engineering','Classics','Cognitive Science','Communication Studies','Computer Engineering',
    'Computer Science','Creative Writing','Criminology','Cultural Studies','Cybersecurity','Dance','Data Science','Dentistry','Design',
    'Development Studies','Digital Business','Earth Sciences','Ecology','Econometrics','Economic History','Economics','Economics and Management',
    'Education','Electrical Engineering','Energy Engineering','Engineering Management','English Language and Literature','Entrepreneurship',
    'Environmental Engineering','Environmental Science','European Studies','Event Management','Fashion Design','Film and Media Studies','Finance',
    'Fine Arts','Food Science','Forestry','Game Design','Gender Studies','Genetics','Geography','Geology','German Studies','Graphic Design',
    'Health Management','Health Sciences','History','Horticulture','Hospitality Management','Human Resource Management','Industrial Engineering',
    'Industrial Engineering and Management','Information Systems','Innovation Management','Insurance','Interior Design','International Business',
    'International Management','International Relations','Journalism','Landscape Architecture','Law','Law and Economics',
    'Library and Information Science','Linguistics','Logistics and Supply Chain Management','Management','Marine Biology','Maritime Studies',
    'Marketing','Materials Science','Mathematics','Mechanical Engineering','Mechatronics','Media and Communication','Medicine','Meteorology',
    'Microbiology','Middle Eastern Studies','Midwifery','Mining Engineering','Modern Languages','Molecular Biology','Museum Studies','Music',
    'Nanotechnology','Neuroscience','Nuclear Engineering','Nursing','Nutrition','Occupational Therapy','Oceanography','Operations Management',
    'Optometry','Performing Arts','Petroleum Engineering','Pharmacology','Pharmacy','Philosophy','Philosophy, Politics and Economics','Photography',
    'Physics','Physiotherapy','Political Science','Project Management','Psychology','Public Administration','Public Health','Public Policy',
    'Quantitative Finance','Radiography','Real Estate','Religious Studies','Robotics','Romance Studies','Social Work','Sociology',
    'Software Engineering','Special Education','Speech and Language Therapy','Sports Management','Sports Science','Statistics','Sustainability',
    'Taxation','Teacher Education','Telecommunications','Theatre Studies','Theology','Tourism Management','Translation and Interpreting',
    'Urban Planning','Veterinary Medicine','Zoology',
],key=str.lower)


def _clean(name):
    return ' '.join(str(name or '').split())


def field_options(current):
    """The classification fields, led by a previously saved value that is not part of the list."""
    current=_clean(current)
    return ([current] if current and current not in FIELDS_OF_STUDY else [])+FIELDS_OF_STUDY


def course_options(shared,own):
    """Shared university course names followed by the student's own, each name once regardless of case."""
    options=[];seen=set()
    for name in [*(shared or []),*(own or [])]:
        name=_clean(name)
        if name and name.lower() not in seen:
            seen.add(name.lower());options.append(name)
    return options


def match_courses(chosen,known):
    """Give typed courses the spelling already in use, and drop blanks and repeats."""
    listed={_clean(name).lower():_clean(name) for name in reversed(known or []) if _clean(name)}
    result=[];seen=set()
    for name in chosen or []:
        name=_clean(name)
        if not name or name.lower() in seen:continue
        seen.add(name.lower());result.append(listed.get(name.lower(),name))
    return result


def load_university_courses(client,university):
    """Course names saved by students at this university; an empty list if it cannot be read."""
    university=_clean(university)
    if len(university)<2:return []
    try:data=client.rpc('university_courses',{'p_university':university}).execute().data
    except Exception:return []
    if not isinstance(data,list):return []
    return [name for name in data if isinstance(name,str) and name.strip()]


def load_universities(client):
    """University names already used by students, each once in its most used spelling; empty if unreadable."""
    try:rows=client.table('profiles').select('university').execute().data
    except Exception:return []
    if not isinstance(rows,list):return []
    counts={}
    for row in rows:
        name=_clean(row.get('university') if isinstance(row,dict) else '')
        if len(name)>=2 and 'prototype catalog' not in name:counts[name]=counts.get(name,0)+1
    best={}
    for name in sorted(counts,key=lambda n:(-counts[n],n)):best.setdefault(name.lower(),name)
    return sorted(best.values(),key=str.lower)

