from answer_order import display_options


def test_answer_tiles_are_stable_within_a_question_without_changing_the_source():
    options=[{'id':letter,'text':letter} for letter in 'abcd']
    first=display_options(options,'session-1',3)
    second=display_options(options,'session-1',3)

    assert [item['id'] for item in first]==[item['id'] for item in second]
    assert [item['id'] for item in options]==list('abcd')


def test_answer_tiles_use_different_positions_across_questions():
    options=[{'id':letter,'text':letter} for letter in 'abcd']
    correct_positions={next(index for index,item in enumerate(display_options(options,'session-1',question)) if item['id']=='a') for question in range(15)}

    assert len(correct_positions)>1
