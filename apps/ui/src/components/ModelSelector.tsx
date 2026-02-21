import type { ModelInfo } from "@/types/api"

import { Select } from "@/components/ui/select"

type ModelSelectorProps = {
  models: ModelInfo[]
  selectedModelId: string
  onChange: (modelId: string) => void
}

export function ModelSelector({ models, selectedModelId, onChange }: ModelSelectorProps) {
  return (
    <div className="w-full max-w-sm">
      <label htmlFor="model-select" className="mb-1 block text-sm font-medium">
        Model
      </label>
      <Select
        id="model-select"
        value={selectedModelId}
        onChange={(event) => onChange(event.target.value)}
        options={models.map((model) => ({
          value: model.model_id,
          label: model.name,
        }))}
      />
    </div>
  )
}
