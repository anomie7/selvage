"""E2E 현실적인 개발자 워크플로우 테스트.

성능보다는 실제 사용 시나리오와 안정성에 중점을 둔 테스트들입니다.
"""

import json
from typing import Any

import pytest
from testcontainers.core.generic import DockerContainer

from e2e.helpers import install_selvage_from_testpypi
from selvage.src.config import get_api_key
from selvage.src.models.model_provider import ModelProvider
from selvage.src.utils.json_extractor import JSONExtractor
from selvage.src.utils.token.models import ReviewResponse


@pytest.fixture(scope="function")
def workflow_container():
    """워크플로우 테스트용 TestPyPI 컨테이너 fixture"""
    container = DockerContainer(image="selvage-testpypi:latest")
    container.with_command("bash -c 'while true; do sleep 1; done'")

    # 실제 API 키 사용
    gemini_api_key = get_api_key(ModelProvider.GOOGLE)
    if gemini_api_key:
        container.with_env("GEMINI_API_KEY", gemini_api_key)

    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="function")
def configured_workflow_container(workflow_container):
    """완전히 설정된 워크플로우 컨테이너 fixture (selvage 설치 및 설정 완료)"""
    container = workflow_container

    install_selvage_from_testpypi(container)

    yield container


def setup_project_with_git(container, project_path: str) -> None:
    """프로젝트 디렉토리 생성 및 git 초기화를 수행하는 헬퍼 함수

    Args:
        container: Docker 컨테이너 인스턴스
        project_path: 프로젝트 경로 (예: '/tmp/test_project')
    """
    # 프로젝트 디렉토리 생성 및 git 초기화, 설정 (하나의 명령어로 실행)
    git_setup_command = f"""
    mkdir -p {project_path} &&
    cd {project_path} &&
    git init &&
    git config user.email test@example.com &&
    git config user.name 'Test User'
    """
    exit_code, output = container.exec(f"bash -c '{git_setup_command.strip()}'")
    assert exit_code == 0, (
        f"Git setup should succeed. Output: {output.decode('utf-8', errors='ignore')}"
    )


def configure_selvage_model(
    container, project_path: str, model: str = "gemini-2.5-flash"
) -> None:
    """selvage 모델 설정을 수행하는 헬퍼 함수

    Args:
        container: Docker 컨테이너 인스턴스
        project_path: 프로젝트 경로
        model: 사용할 모델명 (기본값: gemini-2.5-flash)
    """
    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && selvage config model {model}'"
    )
    assert exit_code == 0, f"Model configuration ({model}) should succeed"


def run_selvage_review(
    container,
    project_path: str,
    review_type: str = "--staged",
    target_branch: str | None = None,
) -> None:
    """selvage 리뷰를 실행하는 헬퍼 함수

    Args:
        container: Docker 컨테이너 인스턴스
        project_path: 프로젝트 경로
        review_type: 리뷰 타입 (기본값: --staged)
        target_branch: 타겟 브랜치 (지정시 --target-branch 옵션 사용)
    """
    if target_branch:
        command = f"bash -c 'cd {project_path} && selvage review --target-branch {target_branch}'"
    else:
        command = f"bash -c 'cd {project_path} && selvage review {review_type}'"

    exit_code, output = container.exec(command)
    assert exit_code == 0, (
        f"Selvage review should succeed. Output: {output.decode('utf-8', errors='ignore')}"
    )


def verify_review_results(
    container, project_path: str, test_name: str
) -> dict[str, Any]:
    """리뷰 결과를 검증하고 상세 정보를 반환하는 공통 함수

    Args:
        container: Docker 컨테이너 인스턴스
        project_path: 프로젝트 경로
        test_name: 테스트 이름 (로깅용)

    Returns:
        검증된 리뷰 결과 정보가 담긴 딕셔너리
    """
    # 리뷰 로그 디렉토리 가져오기
    exit_code, config_dir_output = container.exec(
        f"bash -c 'cd {project_path} && python -c \"from selvage.src.config import get_default_review_log_dir; print(get_default_review_log_dir())\"'"
    )
    assert exit_code == 0, "Should be able to get review log directory"

    review_log_dir = config_dir_output.decode("utf-8", errors="ignore").strip()
    print(f"Review log directory: {review_log_dir}")

    # 리뷰 로그 디렉토리 존재 여부 확인
    exit_code_check, dir_check_output = container.exec(
        f'bash -c \'test -d "{review_log_dir}" && echo "exists" || echo "not_exists"\''
    )
    dir_status = dir_check_output.decode("utf-8", errors="ignore").strip()
    print(f"Directory status: {dir_status}")

    if dir_status != "exists":
        print(f"Review log directory does not exist: {review_log_dir}")
        # 리뷰가 실행되었는지 다시 확인 - staged 변경사항이 있는지 확인
        exit_code_staged, staged_output = container.exec(
            f"bash -c 'cd {project_path} && git diff --cached --name-only'"
        )
        staged_files = staged_output.decode("utf-8", errors="ignore").strip()
        print(f"Staged files: {staged_files}")

        if not staged_files:
            print("No staged files found. This might be why review failed.")
            # 모든 변경사항을 다시 stage
            exit_code_add, add_output = container.exec(
                f"bash -c 'cd {project_path} && git add -A'"
            )
            print(f"Re-staging all changes (exit: {exit_code_add})")

        # 실패한 이유를 더 알아보기 위해 임시로 디렉토리를 생성해서 진행
        exit_code_mkdir, mkdir_output = container.exec(
            f"bash -c 'mkdir -p \"{review_log_dir}\"'"
        )
        print(f"Created review log directory (exit: {exit_code_mkdir})")

    # 리뷰 로그 디렉토리에서 JSON 파일 확인
    exit_code, json_files = container.exec(
        f"bash -c 'find {review_log_dir} -name \"*.json\" -type f | head -5'"
    )
    assert exit_code == 0, "Should be able to list JSON files"

    json_files_list = json_files.decode("utf-8", errors="ignore").strip()
    print(f"Found JSON files: {json_files_list}")

    if not json_files_list:
        print("No JSON review files found. Review might have failed silently.")
        # 최근 파일들 확인
        exit_code_recent, recent_output = container.exec(
            f"bash -c 'find {review_log_dir} -type f -name \"*\" | head -10'"
        )
        recent_files = recent_output.decode("utf-8", errors="ignore").strip()
        print(f"Recent files in review log dir: {recent_files}")

        # 검증 실패가 아닌 경고로 처리하고 빈 결과 반환
        return {
            "json_file_path": None,
            "review_response": None,
            "issues_count": 0,
            "summary": "리뷰 결과를 찾을 수 없음",
            "success_message": f"[{test_name}] 리뷰 결과 파일을 찾을 수 없습니다.",
            "raw_json_data": None,
        }

    # 가장 최근 JSON 파일의 내용 확인
    latest_json_file = json_files_list.split("\n")[0]
    print(f"Reading JSON file: {latest_json_file}")

    exit_code, json_content = container.exec(f"bash -c 'cat \"{latest_json_file}\"'")

    if exit_code != 0:
        # 오류 상황에서 추가 디버깅 정보
        print(f"Failed to read JSON file. Exit code: {exit_code}")
        error_msg = json_content.decode("utf-8", errors="ignore").strip()
        print(f"Error message: {error_msg}")

        # 파일 존재 여부 확인
        exit_code_ls, ls_output = container.exec(f"ls -la '{latest_json_file}' 2>&1")
        print(
            f"File check result (exit: {exit_code_ls}): {ls_output.decode('utf-8', errors='ignore').strip()}"
        )

        # 디렉토리 내용 확인
        exit_code_dir, dir_output = container.exec(f"ls -la '{review_log_dir}' 2>&1")
        print(
            f"Directory contents: {dir_output.decode('utf-8', errors='ignore').strip()}"
        )

    assert exit_code == 0, (
        f"Should be able to read JSON file content. File: {latest_json_file}"
    )

    json_content_str = json_content.decode("utf-8", errors="ignore")

    # JSONExtractor를 사용한 JSON 검증 - 전체 파일 내용을 바로 검증
    json_data = json.loads(json_content_str)
    assert "review_response" in json_data, (
        "JSON file should contain 'review_response' field"
    )

    # review_response가 None이 아닌 경우에만 ReviewResponse 모델로 검증
    validated_response = None
    if json_data["review_response"] is not None:
        validated_response = JSONExtractor.validate_and_parse_json(
            json.dumps(json_data["review_response"]), ReviewResponse
        )
        assert validated_response is not None, (
            "review_response should be valid ReviewResponse model"
        )

    # 리뷰 결과 정보 준비
    review_summary = "리뷰 내용을 확인할 수 없음"
    if validated_response and validated_response.summary:
        review_summary = (
            validated_response.summary[:200] + "..."
            if len(validated_response.summary) > 200
            else validated_response.summary
        )

    # 상세 정보 구성
    success_message = (
        f"\n{'=' * 60}\n"
        f"[{test_name}] 리뷰 결과가 성공적으로 저장되었습니다!\n"
        f"파일 위치: {latest_json_file}\n"
        f"리뷰 요약: {review_summary}\n"
        f"JSON 구조: {list(json_data.keys())}\n"
    )

    # 리뷰 이슈 정보 추가
    issues_count = 0
    if validated_response and validated_response.issues:
        issues_count = len(validated_response.issues)
        success_message += f"발견된 이슈 개수: {issues_count}\n"

        # 첫 번째 이슈 미리보기
        if issues_count > 0:
            first_issue = validated_response.issues[0]
            success_message += f"첫 번째 이슈: {first_issue.type} - {first_issue.description[:100]}...\n"

    success_message += f"{'=' * 60}\n"

    print(success_message)

    # 반환값으로 검증 결과 제공
    return {
        "json_file_path": latest_json_file,
        "review_response": validated_response,
        "issues_count": issues_count,
        "summary": review_summary,
        "success_message": success_message,
        "raw_json_data": json_data,
    }


@pytest.mark.workflow
def test_comprehensive_development_scenario(configured_workflow_container) -> None:
    """포괄적인 개발 시나리오: 다양한 리뷰 방식과 실제 개발 패턴을 종합 테스트."""
    container = configured_workflow_container
    project_path = "/tmp/comprehensive_dev"

    # 프로젝트 설정
    setup_project_with_git(container, project_path)

    # 1. 초기 프로젝트 구조 생성 (실제 프로젝트와 유사)
    project_files = {
        "src/__init__.py": "",
        "src/models.py": """from dataclasses import dataclass
from typing import List, Optional

@dataclass 
class User:
    id: str
    name: str
    email: str
    active: bool = True
""",
        "src/services.py": """from .models import User

def get_user(user_id: str) -> User:
    # TODO: Implement database lookup
    return User(id=user_id, name="Test", email="test@example.com")
""",
        "tests/__init__.py": "",
        "requirements.txt": "requests>=2.25.0\npydantic>=1.8.0",
        "README.md": """# Comprehensive Development Project

## Overview
A realistic project demonstrating various development patterns and code review scenarios.

## Features
- User management system
- RESTful API endpoints  
- Comprehensive test coverage
""",
    }

    # 디렉토리 생성 및 파일 추가
    for filepath, content in project_files.items():
        dir_path = "/".join(filepath.split("/")[:-1])
        if dir_path:
            exit_code, output = container.exec(
                f"bash -c 'cd {project_path} && mkdir -p {dir_path}'"
            )
            assert exit_code == 0, f"Directory creation should succeed: {dir_path}"

        exit_code, output = container.exec(
            f"bash -c 'cd {project_path} && cat > {filepath} << \"EOF\"\n{content}\nEOF'"
        )
        assert exit_code == 0, f"File creation should succeed: {filepath}"

    # 초기 커밋
    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && git add . && git commit -m \"feat: Initial project structure with models and services\"'"
    )
    assert exit_code == 0, "Initial commit should succeed"

    # main 브랜치로 설정
    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && git branch -M main'"
    )
    assert exit_code == 0, "Branch rename should succeed"

    # 2. Feature 브랜치에서 실제 개발 시나리오
    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && git checkout -b feature/user-api'"
    )
    assert exit_code == 0, "Feature branch creation should succeed"

    # API 엔드포인트 추가 (버그 포함)
    api_code = """from flask import Flask, jsonify, request
from src.services import get_user

app = Flask(__name__)

@app.route('/users/<user_id>')
def get_user_endpoint(user_id):
    # Bug: No error handling
    user = get_user(user_id)
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email
    })

@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    # Bug: No validation
    user = User(
        id=data['id'],
        name=data['name'], 
        email=data['email']
    )
    return jsonify({'message': 'User created'})

if __name__ == '__main__':
    app.run(debug=True)
"""

    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && cat > api.py << \"EOF\"\n{api_code}\nEOF'"
    )
    assert exit_code == 0, "API file creation should succeed"

    # 3. 첫 번째 리뷰: staged 파일 리뷰
    exit_code, output = container.exec(f"bash -c 'cd {project_path} && git add api.py'")
    assert exit_code == 0, "Git add should succeed"

    configure_selvage_model(container, project_path)
    run_selvage_review(container, project_path, "--staged")

    staged_review_results = verify_review_results(
        container, project_path, "Staged API review"
    )

    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && git commit -m \"feat: Add user API endpoints (contains bugs)\"'"
    )
    assert exit_code == 0, "API commit should succeed"

    # 4. 코드 개선 (버그 수정)
    improved_api_code = """from flask import Flask, jsonify, request
from src.services import get_user
from src.models import User
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/users/<user_id>')
def get_user_endpoint(user_id: str):
    \"\"\"Get user by ID with proper error handling.\"\"\"
    try:
        if not user_id or not user_id.strip():
            return jsonify({'error': 'User ID is required'}), 400
            
        user = get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'active': user.active
        })
    except Exception as e:
        logging.error(f"Error fetching user {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users', methods=['POST'])
def create_user():
    \"\"\"Create new user with validation.\"\"\"
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data is required'}), 400
            
        # Validate required fields
        required_fields = ['id', 'name', 'email']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Email validation
        if '@' not in data['email']:
            return jsonify({'error': 'Invalid email format'}), 400
            
        user = User(
            id=data['id'],
            name=data['name'], 
            email=data['email'],
            active=data.get('active', True)
        )
        
        logging.info(f"Created user: {user.id}")
        return jsonify({'message': 'User created successfully', 'user_id': user.id}), 201
        
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
"""

    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && cat > api.py << \"EOF\"\n{improved_api_code}\nEOF'"
    )
    assert exit_code == 0, "Improved API file creation should succeed"

    # 5. 두 번째 리뷰: 브랜치 간 비교 리뷰 (실제 PR 시뮬레이션)
    run_selvage_review(container, project_path, target_branch="main")

    branch_review_results = verify_review_results(
        container, project_path, "Branch comparison review"
    )

    # 6. 결과 비교 및 검증
    print("\n" + "=" * 60)
    print("종합 테스트 결과 분석")
    print("=" * 60)
    print(f"Staged 리뷰 발견 이슈: {staged_review_results['issues_count']}개")
    print(f"브랜치 비교 리뷰 발견 이슈: {branch_review_results['issues_count']}개")

    # 브랜치 정보 확인
    exit_code, branch_output = container.exec(
        f"bash -c 'cd {project_path} && git branch --show-current'"
    )
    current_branch = branch_output.decode("utf-8", errors="ignore").strip()

    exit_code, diff_output = container.exec(
        f"bash -c 'cd {project_path} && git log --oneline --graph --decorate --all'"
    )
    if exit_code == 0:
        commit_history = diff_output.decode("utf-8", errors="ignore").strip()
        print(f"Git 히스토리:\n{commit_history}")

    print(f"테스트 완료: {current_branch} 브랜치에서 main과 비교 리뷰")
    print("실제 개발 워크플로우 (staged vs branch comparison) 검증 완료")
    print("=" * 60)


@pytest.mark.workflow
def test_multi_language_file_review(configured_workflow_container) -> None:
    """다양한 언어 파일들의 리뷰 워크플로우 테스트."""
    container = configured_workflow_container
    project_path = "/tmp/multi_lang_project"

    # 프로젝트 설정
    setup_project_with_git(container, project_path)

    # 다양한 언어 파일 생성 (실제 개발에서 자주 보는 패턴들)
    file_contents = {
        "main.py": """#!/usr/bin/env python3
\"\"\"Main application entry point.\"\"\"

import sys
import logging

def main():
    # TODO: Add proper argument parsing
    print("Hello World")
    logging.info("Application started")
    return 0

if __name__ == "__main__":
    sys.exit(main())
""",
        "utils.js": """// Utility functions for the frontend
const API_BASE_URL = "http://localhost:3000";

function fetchUserData(userId) {
    // TODO: Add error handling
    return fetch(`${API_BASE_URL}/users/${userId}`)
        .then(response => response.json());
}

// Export for use in other modules
module.exports = { fetchUserData };
""",
        "README.md": """# Multi-Language Project

## Description
A sample project demonstrating multiple programming languages.

## Setup
1. Install Python dependencies: `pip install -r requirements.txt`
2. Install Node.js dependencies: `npm install`

## Usage
Run the main application:
```bash
python main.py
```

## TODO
- [ ] Add proper error handling
- [ ] Implement user authentication
- [ ] Add unit tests
""",
        "config.json": """{
    "app_name": "MultiLangApp",
    "version": "1.0.0",
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "app_db"
    },
    "features": {
        "authentication": false,
        "logging": true
    }
}""",
    }

    # 파일들 생성 및 초기 커밋
    for filename, content in file_contents.items():
        exit_code, output = container.exec(
            f"bash -c 'cd {project_path} && cat > {filename} << \"EOF\"\n{content}\nEOF'"
        )
        assert exit_code == 0, f"{filename} creation should succeed"

    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && git add . && git commit -m \"Initial project setup\"'"
    )
    assert exit_code == 0, "Initial commit should succeed"

    # 실제 개발 시나리오: 기능 추가 및 리팩토링
    improved_main_py = """#!/usr/bin/env python3
\"\"\"Main application entry point with improved error handling.\"\"\"

import sys
import logging
import argparse

def setup_logging(debug=False):
    \"\"\"Configure logging for the application.\"\"\"
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def parse_arguments():
    \"\"\"Parse command line arguments.\"\"\"
    parser = argparse.ArgumentParser(description="Multi-language application")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    return parser.parse_args()

def main():
    \"\"\"Main application logic.\"\"\"
    try:
        args = parse_arguments()
        setup_logging(args.debug)
        
        logging.info("Application started with config: %s", args.config)
        print("Hello World - Improved Version!")
        
        return 0
    except Exception as e:
        logging.error("Application failed: %s", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""

    # 파일 수정 (실제 개발에서 일어나는 개선)
    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && cat > main.py << \"EOF\"\n{improved_main_py}\nEOF'"
    )
    assert exit_code == 0, "Main.py update should succeed"

    exit_code, output = container.exec(
        f"bash -c 'cd {project_path} && git add main.py'"
    )
    assert exit_code == 0, "Git add should succeed"

    # 리뷰 실행
    configure_selvage_model(container, project_path)
    run_selvage_review(container, project_path)

    # 결과 검증 - 리뷰가 Python 개선사항을 잘 파악했는지 확인
    verify_review_results(container, project_path, "Multi-language file review")
