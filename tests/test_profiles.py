import io
import pytest
from PIL import Image
from logic import validate_profile, crop_photo, render_avatar, DEFAULT_AVATAR, CATALOG

def valid():
    return dict(username="Student_1", university="Nova SBE — prototype catalog",
                courses=["Corporate Finance"], languages=["English"], avatar=DEFAULT_AVATAR.copy())

def test_complete_profile_and_normalization():
    data=valid(); data["username"]=" Student_1 "
    assert validate_profile(**data)["username"]=="Student_1"

@pytest.mark.parametrize("key,value", [
    ("username","a"),("username","bad name"),("university"," "),
    ("courses",[]),("courses",[" "]),("languages",[]),("languages",["Unknown"]),
    ("avatar",{"hair":"<script>"}),
])
# User now permits custom university/course names; blank values remain invalid.
def test_invalid_profile(key,value):
    data=valid(); data[key]=value
    with pytest.raises(ValueError): validate_profile(**data)

def test_avatar_is_deterministic_and_changes():
    a=render_avatar(DEFAULT_AVATAR)
    assert a==render_avatar(DEFAULT_AVATAR)
    b=dict(DEFAULT_AVATAR, hair="Long")
    assert a!=render_avatar(b)
    assert Image.open(io.BytesIO(a)).size==(512,512)  # Higher-resolution avatars requested; photo crops stay 256.

def test_crop_is_square_and_removes_metadata():
    out=io.BytesIO()
    im=Image.new("RGB",(500,300),"red")
    im.save(out,format="JPEG",comment=b"private")
    result=crop_photo(out.getvalue(),0.5,0.5,1)
    parsed=Image.open(io.BytesIO(result))
    assert parsed.size==(256,256)
    assert not parsed.getexif()
    assert "comment" not in parsed.info

@pytest.mark.parametrize("data",[b"not image",b"x"*(5*1024*1024+1)])
def test_invalid_upload(data):
    with pytest.raises(ValueError): crop_photo(data,.5,.5,1)

def test_crop_position_changes_output():
    im=Image.new("RGB",(600,300),"red")
    im.paste("blue",(300,0,600,300)); out=io.BytesIO();im.save(out,format="PNG")
    assert crop_photo(out.getvalue(),0,.5,1)!=crop_photo(out.getvalue(),1,.5,1)
