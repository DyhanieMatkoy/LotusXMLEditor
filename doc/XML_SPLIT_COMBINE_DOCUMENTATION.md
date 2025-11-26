# XML Split and Combine Documentation

## Overview

The Lotus Xml Editor provides powerful functionality to split large XML files into manageable parts and combine multiple XML files into a single document. This documentation explains the configuration options and provides practical examples.

## Split Configuration Structure

### Basic Configuration

```json
{
  "split_config": {
    "threshold_percentage": 15.0,
    "upper_levels": [2, 3, 4],
    "rules": [
      {
        "rule_type": "threshold",
        "criteria": "15.0%",
        "priority": 1,
        "preserve_context": true,
        "enabled": true
      }
    ],
    "output_directory": "./xml_split_output",
    "backup_original": true
  }
}
```

### Configuration Parameters Explained

#### `threshold_percentage` (float)
- **Purpose**: Defines the size threshold for splitting as a percentage of the original file
- **Range**: 1.0 - 50.0
- **Example**: `15.0` means each part should be approximately 15% of the original file size
- **Usage**: Larger values create fewer, bigger parts; smaller values create more, smaller parts

#### `upper_levels` (array of integers)
- **Purpose**: Specifies which XML hierarchy levels to consider for splitting
- **Values**: Depth levels starting from root (1 = root level)
- **Example**: `[2, 3, 4]` considers elements at depths 2, 3, and 4 for potential split points
- **Strategy**: Lower levels create larger chunks, higher levels create more granular splits

#### `rules` (array of rule objects)
Defines the splitting logic with multiple rule types:

##### Threshold Rule
```json
{
  "rule_type": "threshold",
  "criteria": "15.0%",
  "priority": 1,
  "preserve_context": true,
  "enabled": true
}
```

##### Element-based Rule
```json
{
  "rule_type": "element",
  "criteria": "Product",
  "priority": 2,
  "preserve_context": true,
  "enabled": true
}
```

##### Depth-based Rule
```json
{
  "rule_type": "depth",
  "criteria": "3",
  "priority": 3,
  "preserve_context": false,
  "enabled": true
}
```

##### Size-based Rule
```json
{
  "rule_type": "size",
  "criteria": "1MB",
  "priority": 4,
  "preserve_context": true,
  "enabled": true
}
```

##### XPath-based Rule
```json
{
  "rule_type": "xpath",
  "criteria": "//catalog/product[@category='electronics']",
  "priority": 5,
  "preserve_context": true,
  "enabled": true
}
```

### Rule Parameters

- **`rule_type`**: Type of splitting rule (threshold, element, depth, size, xpath)
- **`criteria`**: Rule-specific criteria (percentage, element name, depth number, size, XPath expression)
- **`priority`**: Execution order (lower numbers = higher priority)
- **`preserve_context`**: Whether to maintain parent element structure in split parts
- **`enabled`**: Whether this rule is active

## Tutorial: Splitting XML into 3 Parts

### Step 1: Open the Split Dialog

1. Load your XML file in the Visual XML Editor
2. Go to **XML** menu → **Split XML...** or click the **Split XML** toolbar button
3. The Split Configuration Dialog will open

### Step 2: Configure for 3-Part Split

#### Method A: Threshold-Based Splitting
```json
{
  "threshold_percentage": 33.0,
  "upper_levels": [2, 3],
  "rules": [
    {
      "rule_type": "threshold",
      "criteria": "33.0%",
      "priority": 1,
      "preserve_context": true,
      "enabled": true
    }
  ]
}
```

**Configuration Steps:**
1. Set **Threshold Percentage** to `33.0`
2. Check **Upper Levels** 2 and 3
3. Ensure the threshold rule is enabled
4. Set **Preserve Context** to maintain XML structure

#### Method B: Element-Based Splitting
For XML with repeating elements (e.g., products, records, entries):

```json
{
  "threshold_percentage": 33.0,
  "upper_levels": [2, 3, 4],
  "rules": [
    {
      "rule_type": "element",
      "criteria": "Product",
      "priority": 1,
      "preserve_context": true,
      "enabled": true
    },
    {
      "rule_type": "threshold",
      "criteria": "33.0%",
      "priority": 2,
      "preserve_context": true,
      "enabled": true
    }
  ]
}
```

**Configuration Steps:**
1. Add an **Element Rule** with your target element name (e.g., "Product", "Record", "Item")
2. Set **Priority** to 1 (highest)
3. Add a **Threshold Rule** as fallback with priority 2
4. Set threshold to 33% to aim for 3 parts

#### Method C: Mixed Strategy for Complex XML
```json
{
  "threshold_percentage": 33.0,
  "upper_levels": [2, 3, 4, 5],
  "rules": [
    {
      "rule_type": "depth",
      "criteria": "3",
      "priority": 1,
      "preserve_context": true,
      "enabled": true
    },
    {
      "rule_type": "size",
      "criteria": "500KB",
      "priority": 2,
      "preserve_context": true,
      "enabled": true
    },
    {
      "rule_type": "threshold",
      "criteria": "33.0%",
      "priority": 3,
      "preserve_context": true,
      "enabled": true
    }
  ]
}
```

### Step 3: Execute the Split

1. Click **Analyze XML** to preview the split strategy
2. Review the analysis results showing:
   - Estimated number of parts
   - Split points
   - Size distribution
3. Adjust configuration if needed
4. Click **Split XML** to execute
5. Choose output directory
6. Enable **Backup Original** for safety

### Step 4: Verify Results

After splitting, you'll get:
- `metadata.json` - Split project information
- `parts/` directory containing:
  - `part_001.xml` - First part
  - `part_002.xml` - Second part
  - `part_003.xml` - Third part
  - `original.xml` - Backup (if enabled)

## Example Scenarios

### Scenario 1: E-commerce Catalog
**XML Structure:**
```xml
<catalog>
  <products>
    <product id="1">...</product>
    <product id="2">...</product>
    <!-- 1000+ products -->
  </products>
</catalog>
```

**Optimal Configuration:**
```json
{
  "threshold_percentage": 33.0,
  "upper_levels": [3],
  "rules": [
    {
      "rule_type": "element",
      "criteria": "product",
      "priority": 1,
      "preserve_context": true,
      "enabled": true
    }
  ]
}
```

### Scenario 2: Financial Data
**XML Structure:**
```xml
<financial_data>
  <transactions>
    <transaction>...</transaction>
  </transactions>
  <accounts>
    <account>...</account>
  </accounts>
  <reports>
    <report>...</report>
  </reports>
</financial_data>
```

**Optimal Configuration:**
```json
{
  "threshold_percentage": 33.0,
  "upper_levels": [2, 3],
  "rules": [
    {
      "rule_type": "depth",
      "criteria": "2",
      "priority": 1,
      "preserve_context": true,
      "enabled": true
    }
  ]
}
```

### Scenario 3: Large Configuration File
**XML Structure:**
```xml
<configuration>
  <settings>
    <!-- Many nested settings -->
  </settings>
  <modules>
    <!-- Complex module definitions -->
  </modules>
  <data>
    <!-- Large data sections -->
  </data>
</configuration>
```

**Optimal Configuration:**
```json
{
  "threshold_percentage": 33.0,
  "upper_levels": [2, 3, 4],
  "rules": [
    {
      "rule_type": "size",
      "criteria": "1MB",
      "priority": 1,
      "preserve_context": true,
      "enabled": true
    },
    {
      "rule_type": "threshold",
      "criteria": "33.0%",
      "priority": 2,
      "preserve_context": true,
      "enabled": true
    }
  ]
}
```

## Combine Functionality

### Combine Methods

#### 1. Merge Root Elements
Combines XML files by merging their root element children:
```xml
<!-- Input files -->
<!-- file1.xml -->
<root><item>A</item></root>
<!-- file2.xml -->
<root><item>B</item></root>

<!-- Output -->
<root>
  <item>A</item>
  <item>B</item>
</root>
```

#### 2. Wrap in New Root
Wraps all files in a new root element:
```xml
<!-- Output -->
<combined_root>
  <root><item>A</item></root>
  <root><item>B</item></root>
</combined_root>
```

#### 3. Simple Concatenation
Concatenates files with XML declaration:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<root><item>A</item></root>
<root><item>B</item></root>
```

### Using the Combine Dialog

1. Open **File Navigator** (View → Show File Navigator)
2. Select multiple XML files
3. Click **Combine Files** button
4. Choose combination method
5. Set output file name
6. Click **Combine** to execute

## Best Practices

### For Splitting
1. **Always backup** your original file
2. **Analyze first** before splitting to understand the structure
3. **Use element-based rules** for structured, repetitive data
4. **Use threshold rules** for mixed or unknown structures
5. **Preserve context** unless you need standalone parts
6. **Test with small files** first to validate your configuration

### For Combining
1. **Validate XML** files before combining
2. **Check encoding** consistency across files
3. **Use merge method** for similar structured files
4. **Use wrap method** for different root elements
5. **Preview results** before saving

## Troubleshooting

### Common Issues

**Split creates too many/few parts:**
- Adjust `threshold_percentage`
- Modify `upper_levels` range
- Add/remove rules with different priorities

**Split points are not optimal:**
- Use element-based rules for structured data
- Adjust depth levels in `upper_levels`
- Enable `preserve_context` for better structure

**Combine fails with validation errors:**
- Check XML syntax in source files
- Ensure consistent encoding
- Validate namespace declarations

**Performance issues with large files:**
- Use size-based rules to limit part sizes
- Reduce `upper_levels` range
- Disable `preserve_context` if not needed

## Advanced Features

### XPath-Based Splitting
For complex XML structures, use XPath expressions:
```json
{
  "rule_type": "xpath",
  "criteria": "//section[@type='data']/record",
  "priority": 1,
  "preserve_context": true,
  "enabled": true
}
```

### Custom Split Strategies
Combine multiple rules for sophisticated splitting:
```json
{
  "rules": [
    {
      "rule_type": "element",
      "criteria": "chapter",
      "priority": 1,
      "preserve_context": true,
      "enabled": true
    },
    {
      "rule_type": "size",
      "criteria": "2MB",
      "priority": 2,
      "preserve_context": true,
      "enabled": true
    },
    {
      "rule_type": "threshold",
      "criteria": "25.0%",
      "priority": 3,
      "preserve_context": true,
      "enabled": true
    }
  ]
}
```

This configuration will:
1. First try to split at `<chapter>` elements
2. If parts exceed 2MB, split further
3. As fallback, ensure no part exceeds 25% of original size

---

*For more information and updates, refer to the Lotus Xml Editor documentation or contact support.*