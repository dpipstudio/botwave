import os

class SecurityError(Exception):
    pass

class PathValidator:    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to prevent path traversal.
        
        Args:
            filename: The filename to sanitize
            
        Returns:
            Safe filename (basename only, no path components)
            
        Raises:
            SecurityError: If filename is invalid or dangerous
        """
        if not filename:
            raise SecurityError("Filename cannot be empty")
        
        filename = filename.replace('\x00', '')

        for char in ['..', '/', '\\']:
            if char in filename:
                raise SecurityError(f"Illegal character sequence in filename: {char}")
        
        basename = os.path.basename(filename)
        
        if not basename or basename in ('.', '..'):
            raise SecurityError("Invalid filename after sanitization")
        
        return basename
    
    @staticmethod
    def path_indir(filepath: str, allowed_dir: str, must_exist: bool = False) -> str:
        """
        Verify that a file path is within an allowed directory.
        Returns the real absolute path if valid.
        
        Args:
            filepath: The file path to validate
            allowed_dir: The directory that must contain the file
            must_exist: If True, path must exist on filesystem
            
        Returns:
            Real absolute path
            
        Raises:
            SecurityError: If path is outside allowed directory or invalid
        """
        try:
            allowed_real = os.path.realpath(os.path.abspath(allowed_dir))
            
            if os.path.exists(filepath):
                file_real = os.path.realpath(os.path.abspath(filepath))
            else:
                if must_exist:
                    raise SecurityError(f"Path does not exist: {filepath}")
                # Construct expected path
                file_real = os.path.realpath(os.path.abspath(filepath))
            
            try:
                common = os.path.commonpath([allowed_real, file_real])
                if common != allowed_real:
                    raise SecurityError(f"Path traversal detected: {filepath} is outside {allowed_dir}")
            except ValueError:
                raise SecurityError(f"Path traversal detected: {filepath} is outside {allowed_dir}")
            
            return file_real
            
        except (OSError, ValueError) as e:
            raise SecurityError(f"Invalid path: {e}")
    
    @staticmethod
    def safe_join(base_dir: str, *paths: str) -> str:
        """
        Safely join paths and validate result is within base_dir.
        
        Args:
            base_dir: Base directory
            *paths: Path components to join
            
        Returns:
            Safe joined path
            
        Raises:
            SecurityError: If resulting path escapes base_dir
        """
        safe_paths = []
        for path in paths:
            if not path:
                continue
            safe_component = os.path.basename(path)
            if not safe_component or safe_component in ('.', '..'):
                raise SecurityError(f"Invalid path component: {path}")
            safe_paths.append(safe_component)
        
        result = os.path.join(base_dir, *safe_paths)
        
        return PathValidator.path_indir(result, base_dir)
    
    @staticmethod
    def validate_read(source_path: str, allowed_dirs: list) -> str:
        """
        Validate a source path for reading is in allowed directories.
        
        Args:
            source_path: Path to validate
            allowed_dirs: List of allowed directories
            
        Returns:
            Real absolute path
            
        Raises:
            SecurityError: If path is not in allowed directories
        """
        if not allowed_dirs:
            raise SecurityError("No allowed directories specified")
        
        real_path = os.path.realpath(os.path.abspath(source_path))
        
        for allowed_dir in allowed_dirs:
            try:
                allowed_real = os.path.realpath(os.path.abspath(allowed_dir))
                common = os.path.commonpath([allowed_real, real_path])
                if common == allowed_real:
                    return real_path  # valid
            except (ValueError, OSError):
                continue
        
        raise SecurityError(f"Access denied: {source_path} is not in allowed directories")
