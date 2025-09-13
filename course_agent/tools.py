import json
import os
from datetime import datetime


def save_course_to_file(course_json: str, filename: str) -> dict:
    """Saves the course structure to a JSON file."""
    try:
        course_data = json.loads(course_json)
        with open(filename, "w") as f:
            json.dump(course_data, f, indent=2)
        return {"status": "success", "message": f"Course saved to {filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def analyze_tech_stack(technologies: str) -> dict:
    """Analyzes the provided technologies/frameworks for course context."""
    tech_list = [tech.strip() for tech in technologies.split(",")]
    
    tech_analysis = {
        "technologies": tech_list,
        "categories": [],
        "suggested_topics": [],
        "difficulty_recommendations": {}
    }
    
    # Basic categorization
    web_frameworks = ["react", "vue", "angular", "fastapi", "flask", "django", "express"]
    data_tools = ["python", "pandas", "numpy", "tensorflow", "pytorch", "scikit-learn"]
    cloud_tools = ["aws", "gcp", "azure", "docker", "kubernetes"]
    
    for tech in tech_list:
        tech_lower = tech.lower()
        if any(fw in tech_lower for fw in web_frameworks):
            tech_analysis["categories"].append("Web Development")
        elif any(dt in tech_lower for dt in data_tools):
            tech_analysis["categories"].append("Data Science/ML")
        elif any(ct in tech_lower for ct in cloud_tools):
            tech_analysis["categories"].append("Cloud/DevOps")
    
    tech_analysis["analysis_timestamp"] = datetime.now().isoformat()
    return tech_analysis


def validate_course_structure(course_json: str) -> dict:
    """Validates the course structure for completeness."""
    try:
        course = json.loads(course_json)
        
        required_fields = ["title", "description", "modules", "difficulty_level"]
        missing_fields = [field for field in required_fields if field not in course]
        
        if missing_fields:
            return {
                "valid": False, 
                "errors": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        if not course.get("modules"):
            return {"valid": False, "errors": "Course must have at least one module"}
        
        for i, module in enumerate(course["modules"]):
            if not module.get("lessons"):
                return {
                    "valid": False, 
                    "errors": f"Module {i+1} must have at least one lesson"
                }
        
        return {"valid": True, "message": "Course structure is valid"}
    
    except json.JSONDecodeError:
        return {"valid": False, "errors": "Invalid JSON format"}