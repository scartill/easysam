def validate(resources_data: dict, errors: list[str]):
    if 'prefix' not in resources_data:
        errors.append('No prefix found in resources')
        return
