# cc-sessions Hooks Validation Guide

This guide explains how to validate that the new cc-sessions hooks work correctly and provide the expected improvements to the user experience.

## Quick Start

### 1. Quick Test (Recommended First Step)

```bash
python quick_test.py
```

This runs basic functionality tests and should complete in under 30 seconds.

### 2. Full Validation Suite

```bash
python validate_implementation.py
```

This runs all validation tests including unit tests, integration tests, UX validation, and performance benchmarks.

## Validation Scripts

### 1. `quick_test.py` - Quick Functionality Test

**Purpose**: Fast validation of basic hook functionality
**Duration**: ~30 seconds
**What it tests**:

- Basic hook execution
- Unsafe operation blocking
- Context preservation file creation
- Analytics generation

**Usage**:

```bash
python quick_test.py
```

### 2. `test_hooks.py` - Unit Tests

**Purpose**: Comprehensive unit testing of individual hooks
**Duration**: ~2-3 minutes
**What it tests**:

- Individual hook functionality
- Parameter validation
- Error handling
- File creation and state management

**Usage**:

```bash
python test_hooks.py
```

### 3. `integration_test.py` - Integration Tests

**Purpose**: Test hooks working together in realistic scenarios
**Duration**: ~3-5 minutes
**What it tests**:

- Complete workflow integration
- Hook interaction
- Performance improvements
- Error reduction

**Usage**:

```bash
python integration_test.py
```

### 4. `ux_validation.py` - User Experience Validation

**Purpose**: Measure UX improvements from the new hooks
**Duration**: ~2-3 minutes
**What it tests**:

- Tool execution error reduction
- Context efficiency improvements
- Manual intervention reduction
- User satisfaction metrics

**Usage**:

```bash
python ux_validation.py
```

### 5. `performance_benchmark.py` - Performance Testing

**Purpose**: Ensure hooks don't significantly impact performance
**Duration**: ~5-10 minutes
**What it tests**:

- Hook execution time
- Memory usage
- System throughput
- Context processing performance

**Usage**:

```bash
python performance_benchmark.py
```

### 6. `validate_implementation.py` - Complete Validation

**Purpose**: Run all validation tests in sequence
**Duration**: ~15-20 minutes
**What it tests**:

- All unit tests
- All integration tests
- UX validation
- Performance benchmarks
- Manual validation checks

**Usage**:

```bash
python validate_implementation.py
```

## Expected Results

### Quick Test Results

- ✅ All hooks execute without errors
- ✅ Unsafe operations are properly blocked
- ✅ Context preservation files are created
- ✅ Analytics files are generated

### Full Validation Results

- **Unit Tests**: 100% pass rate
- **Integration Tests**: All scenarios pass
- **UX Validation**: 70%+ improvement in key metrics
- **Performance**: All hooks meet performance thresholds
- **Manual Validation**: All checks pass

## Troubleshooting

### Common Issues

1. **Hook not found errors**

   - Ensure you're running from the project root directory
   - Check that all hook files exist in `cc_sessions/hooks/`

2. **Permission denied errors**

   - Make sure scripts are executable: `chmod +x *.py`
   - Check file permissions on hook files

3. **Timeout errors**

   - Some tests may timeout on slower systems
   - Increase timeout values in the test scripts if needed

4. **Missing dependencies**
   - Install required Python packages: `pip install psutil` (for performance testing)

### Debug Mode

To run tests with more verbose output:

```bash
python -u quick_test.py 2>&1 | tee test_output.log
```

## Validation Metrics

### Performance Thresholds

- **Hook execution time**: < 1 second per hook
- **Memory usage**: < 50MB per hook
- **Context processing**: < 2 seconds
- **Throughput**: > 10 operations per second

### UX Improvement Targets

- **Tool execution errors**: 50%+ reduction
- **Context efficiency**: 20%+ improvement
- **Manual interventions**: 60%+ reduction
- **User satisfaction**: 7.5+ on 1-10 scale

## Report Files

Validation generates several report files in `.claude/` directory:

- `test_report.json` - Unit test results
- `integration_report.json` - Integration test results
- `ux_validation_report.json` - UX validation results
- `performance_benchmark_report.json` - Performance results
- `validation_report.json` - Overall validation summary

## Continuous Validation

To run validation automatically:

```bash
# Add to your CI/CD pipeline
python validate_implementation.py && echo "Validation passed" || echo "Validation failed"
```

## Support

If you encounter issues with validation:

1. Check the troubleshooting section above
2. Review the generated report files
3. Run individual test scripts to isolate issues
4. Check the hook implementation for errors

## Next Steps

After successful validation:

1. The hooks are ready for production use
2. Monitor performance in real-world scenarios
3. Collect user feedback on UX improvements
4. Consider additional optimizations based on usage patterns
