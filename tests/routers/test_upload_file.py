from unittest.mock import patch
from io import BytesIO
from fastapi import HTTPException
from src.models.file_upload import UploadFileResponse

# =========================== SUCCESS =========================== #

good_save_response = UploadFileResponse(success="File saved successfully in test_bucket with key test_file.txt",
                                        checksum="ABC123", version_id="1000000", file_already_existed=False)

good_folder_save_response = UploadFileResponse(success="File saved successfully in test_bucket with key "
                                               "yet_another_test_folder/test_file.txt",
                                               checksum="GHI789", version_id="3000000", file_already_existed=False)


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_success(handler_mock, test_client):
    handler_mock.return_value = good_save_response

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt",
                               "checksum": "ABC123", "version_id": "1000000", "file_already_existed": False}

    handler_mock.assert_called_once()


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_with_empty_body_processed_successfully(handler_mock, test_client):
    handler_mock.return_value = good_save_response

    data = {
        "body": "{}"
    }

    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt",
                               "checksum": "ABC123", "version_id": "1000000", "file_already_existed": False}


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_with_with_irrelevant_body_processed_successfully(handler_mock, test_client):
    handler_mock.return_value = good_save_response

    # Details below are not relevant as they do not correspond with FileUpload model
    data = {"body": '{"bucketName": "test_bucket", "speed": "extra medium"}'}

    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key test_file.txt",
                               "checksum": "ABC123", "version_id": "1000000", "file_already_existed": False}


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_with_with_body_folder_value_processed_successfully(handler_mock, test_client):
    handler_mock.return_value = good_folder_save_response

    data = {"body": '{"folder": "yet_another_test_folder"}'}

    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 201
    assert response.json() == {"success": "File saved successfully in test_bucket with key "
                               "yet_another_test_folder/test_file.txt",
                               "checksum": "GHI789", "version_id": "3000000", "file_already_existed": False}
    # Check that the folder specified in request body has been forwarded to file handler in FileUpload object
    # Note will likley need updating if FileUpload model has new attributes
    assert "FileUpload(folder='yet_another_test_folder'" in str(handler_mock.call_args)


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_with_valid_replacement_filename_uses_replacement_filename(handler_mock, test_client):
    replacement_filename = "new_name.txt"

    handler_mock.return_value = UploadFileResponse(success="File saved successfully in test_bucket with key "
                                                   f"{replacement_filename}",
                                                   checksum="GHI789", version_id="3000000", file_already_existed=False)

    # Fiddly formatting of value - (1) str representation of json, not dict (2) f-string with literal { & } (doubled)
    data = {"body": f'{{"replacement_filename": "{replacement_filename}"}}'}
    files = {
        "file": ("original_name.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)
    assert response.status_code == 201

    # Checking the mock handler is given the right filename in its args file object.
    # Note a too broad string comparison with handler_mock.call_args will still find
    # the original filename because it's present in the request which is also an arg
    _, kwargs = handler_mock.call_args
    assert replacement_filename == kwargs["file"].filename

    # Asserts below are weak as they just check the mock return value established above.
    assert replacement_filename in response.text
    assert "original_name.txt" not in response.json()


# =========================== FAILURE =========================== #


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_with_virus(handler_mock, test_client):
    handler_mock.side_effect = HTTPException(status_code=400, detail="Virus detected")

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("infected_file.txt", BytesIO(b"malicious content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Virus detected"}

    handler_mock.assert_called_once()


@patch("src.routers.save_file.handle_file_upload_logic", return_value=({}, False))
def test_save_file_no_file(handler_mock, test_client):

    handler_mock.side_effect = HTTPException(
        status_code=400,
        detail="File is required"
    )
    data = {
        "body": '{"bucketName": "test_bucket"}'
    }

    response = test_client.post("/save_file", data=data)

    assert response.status_code == 400
    assert response.json() == {'detail': 'File is required'}

    handler_mock.assert_called_once()


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_invalid_data(handler_mock, test_client):
    data = {
        "body": "bad body"
    }
    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 400

    handler_mock.assert_not_called()  # bad JSON fails before calling handler


@patch("src.routers.save_file.handle_file_upload_logic")
def test_save_file_existing_file(handler_mock, test_client):

    handler_mock.side_effect = HTTPException(
        status_code=409,
        detail="File already exists"
    )

    data = {
        "body": '{"bucketName": "test_bucket"}'
    }
    files = {
        "file": ("test_file.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 409
    assert response.json()["detail"] == "File already exists"

    handler_mock.assert_called_once()


def test_save_file_with_duplicate_replacement_filename_returns_error(test_client):
    data = {"body": '{"replacement_filename": "original_name.txt"}'}

    files = {
        "file": ("original_name.txt", BytesIO(b"Test content"), "text/plain")
    }

    response = test_client.post("/save_file", data=data, files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == ("Replacement filename can't be the same as original filename. "
                                         "Both are: original_name.txt")
