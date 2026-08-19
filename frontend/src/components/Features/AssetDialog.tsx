import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type AssetKind,
  type FeatureAssetPublic,
  FeaturesService,
  type FilePublic,
} from "@/client"
import { FileUpload } from "@/components/Common/FileUpload"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { ASSET_KIND_SINGULAR } from "./constants"
import { PartSelect } from "./PartSelect"

const formSchema = z.object({
  name: z.string().min(1, { message: "El nombre es obligatorio" }),
})

type FormData = z.infer<typeof formSchema>

/** Extensiones tipicas por tipo de adjunto, solo como ayuda del selector. */
const ACCEPT: Record<AssetKind, string> = {
  mold: ".step,.stp,.igs,.iges,.catpart,.sldprt",
  part: ".step,.stp,.igs,.iges,.catpart,.sldprt",
  scan: ".stl,.ply,.obj,.txt",
  drawing: ".pdf",
  moldflow: ".mfr,.mpi,.zip",
}

interface AssetDialogProps {
  featureId: string
  kind: AssetKind
  /** null = crear; con asset = editar. */
  asset: FeatureAssetPublic | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** Alta y edicion de una pieza ejemplo (molde CAD, pieza ref. o plano 2D). */
export function AssetDialog({
  featureId,
  kind,
  asset,
  open,
  onOpenChange,
}: AssetDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [file, setFile] = useState<FilePublic | null>(null)
  const [partId, setPartId] = useState<string | null>(null)

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: { name: "" },
  })

  useEffect(() => {
    if (open) {
      form.reset({ name: asset?.name ?? "" })
      setFile(asset?.file ?? null)
      setPartId(asset?.part?.id ?? null)
    }
  }, [open, asset, form])

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      const body = {
        name: data.name,
        part_id: partId,
        file_id: file?.id ?? null,
      }
      return asset
        ? FeaturesService.updateFeatureAsset({
            assetId: asset.id,
            requestBody: body,
          })
        : FeaturesService.createFeatureAsset({
            featureId,
            requestBody: { ...body, kind },
          })
    },
    onSuccess: () => {
      showSuccessToast(asset ? "Adjunto actualizado" : "Adjunto anadido")
      onOpenChange(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["features"] })
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {asset ? "Editar" : "Anadir"} {ASSET_KIND_SINGULAR[kind]}
          </DialogTitle>
          <DialogDescription>
            Adjunta el fichero e indica a que pieza o molde pertenece.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))}>
            <div className="grid gap-4 py-2">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Nombre <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input placeholder="CAD nombre" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="space-y-2">
                <Label>Pieza</Label>
                <PartSelect value={partId} onChange={setPartId} allowEmpty />
              </div>
              <div className="space-y-2">
                <Label>Fichero</Label>
                <FileUpload
                  value={file}
                  onChange={setFile}
                  accept={ACCEPT[kind]}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={mutation.isPending}
              >
                Cancelar
              </Button>
              <LoadingButton type="submit" loading={mutation.isPending}>
                {asset ? "Guardar" : "Anadir"}
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
